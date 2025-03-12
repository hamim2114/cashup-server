from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator


# Buyer Model
class Buyer(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    membership_status = models.BooleanField(default=False)
    main_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    date_of_birth = models.DateField(null=True, blank=True)

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    buyer_image = models.CharField(max_length=500, blank=True, null=True, help_text="URL of the buyer image")
    
    groups = models.ManyToManyField("auth.Group", related_name='buyers', blank=True)
    user_permissions = models.ManyToManyField("auth.Permission", related_name='buyers_permissions', blank=True)

    def save(self, *args, **kwargs):

        if not self.username:
            self.username = self.phone_number  # Use phone number as username if not provided
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class WithdrawalFromCompoundingProfit(models.Model):
    buyer = models.ForeignKey('Buyer', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending")
    date=models.DateTimeField(default=timezone.now)    
    def __str__(self):
        return f"Withdrawal request by {self.buyer.name} for {self.amount} - {self.status}"
    

class WithdrawalFromMainBalance(models.Model):
    buyer = models.ForeignKey('Buyer', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending")
    date=models.DateTimeField(default=timezone.now) 
    def __str__(self):
        return f"Withdrawal request by {self.buyer.name} for {self.amount} - {self.status}"


class WithdrawalFromCashupBalance(models.Model):
    buyer = models.ForeignKey('Buyer', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending")
    date=models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Withdrawal request by {self.buyer.name} for {self.amount} - {self.status}"


# Category Model
class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# Item Model
class Item(models.Model):
    name = models.CharField(max_length=255, help_text="Name of the product")
    description = models.TextField(blank=True, help_text="Description of the product")
    is_available = models.BooleanField(default=True, help_text="Availability status of the product")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    members_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    item_image = models.CharField(max_length=500, blank=True, null=True, help_text="Image of the product")

    

    def __str__(self):
        return self.name


# OTP Model for Buyer
class BuyerOTP(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name='otps')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.buyer.phone_number} - {self.otp}"

    def is_expired(self):
        """Check if the OTP has expired (e.g., after 5 minutes)."""
        return timezone.now() > self.created_at + timedelta(minutes=5)


# Purchase Model
class Purchase(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    discount_total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, null=False, default=1, related_name='purchase')
    confirmed = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    membership_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True)
    total_membership_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.item:
            item_price = self.item.price
            self.total_price = item_price * self.quantity
        
        if self.item:
            self.membership_price = self.item.members_price  
            self.total_membership_price = self.membership_price * self.quantity


        if self.item:
            self.discount_price = self.item.discount_price
            self.total_price = self.discount_price*self.quantity


        else:
            self.discount_price = item_price
            self.discount_total_price = self.total_price

        if self.confirmed and self.paid:
            if self.buyer.main_balance < self.discount_total_price:
                raise ValueError("Insufficient balance to complete the purchase.")
            else:
                self.buyer.main_balance -= self.discount_total_price
                self.buyer.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Purchase {self.id} by {self.buyer}"


# Cashup Owing Deposit Model
from django.db import models
from decimal import Decimal

class CashupOwingDeposit(models.Model):
    requested_cashup_owing_main_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cashup_owing_main_balance = models.DecimalField(max_digits=10, decimal_places=2)
    cashup_owing_dps=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    buyer = models.ForeignKey('Buyer', on_delete=models.SET_NULL, null=True, related_name='cashup_owing_deposits')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    daily_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    compounding_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    withdraw = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    product_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    compounding_withdraw = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    daily_compounding_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_compounding_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_by = models.ForeignKey(Buyer, on_delete=models.SET_NULL, null=True, blank=True)
    verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Ensure updated_by is the same as the buyer field
        if self.buyer and not self.updated_by:
            self.updated_by = self.buyer  # Set updated_by to the same as the buyer
        
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Owing Deposit: {self.cashup_owing_main_balance} by {self.buyer.name if self.buyer else 'Unknown Buyer'}"


# Cashup Deposit Model
class CashupDeposit(models.Model):
    cashup_main_balance = models.DecimalField(max_digits=10, decimal_places=2)
    buyer = models.ForeignKey(Buyer, on_delete=models.SET_NULL, null=True, related_name='cashup_deposits')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    daily_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    compounding_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    withdraw = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    product_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    compounding_withdraw = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    daily_compounding_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_compounding_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_by = models.ForeignKey(Buyer, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Deposit: {self.cashup_main_balance} by {self.buyer.name if self.buyer else 'Unknown Buyer'}"

    def save(self, *args, **kwargs):
        
        if self.buyer and not self.updated_by:
            self.updated_by = self.buyer  # S
        # Check if cashup_main_balance > 0 and update the buyer's membership_status
        if self.cashup_main_balance > 0:
            if self.buyer:
                self.buyer.membership_status = True
                self.buyer.save()  # Save the buyer's membership status change
        else:
            if self.buyer:
                self.buyer.membership_status = False
                self.buyer.save()
        super().save(*args, **kwargs)


# Buyer Transaction Model
from django.db import models, transaction
from decimal import Decimal
from django.db import models, transaction
from decimal import Decimal

class BuyerTransaction(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    METHOD_CHOICES = [
        ('Bkash', 'BKash'),
        ('Nagad', 'Nagad'),
        ('Rocket','Rocket')
    ]
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='Bkash')
    verified = models.BooleanField(default=False)
    date=models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.buyer:
            raise ValueError("Buyer does not exist")

        with transaction.atomic():  # Ensure atomicity
            # Fetch or create CashupOwingDeposit for the buyer
            cashup_owing_deposit, created  = CashupOwingDeposit.objects.get_or_create(
                buyer=self.buyer,
                defaults={
                    'cashup_owing_main_balance': Decimal('0.00'),
                    'requested_cashup_owing_main_balance': Decimal('0.00'),
                    'verified': False,
                }
            )
            if created or cashup_owing_deposit.pk is None:
                cashup_owing_deposit.save()

            # Handle fetching the CashupDeposit safely with filter()
            cashup_deposit = CashupDeposit.objects.filter(buyer=self.buyer).first()
            if not cashup_deposit:
                cashup_deposit = CashupDeposit.objects.create(
                    buyer=self.buyer,
                    cashup_main_balance=Decimal('0.00')
                )
            if self.verified:
                # If cashup_owing_main_balance is positive
                if cashup_owing_deposit.cashup_owing_main_balance > 0:
                    # Deduct from cashup_owing_dps first
                    if self.amount <= cashup_owing_deposit.cashup_owing_dps:
                        cashup_owing_deposit.cashup_owing_dps -= self.amount  # Deduct from DPS
                        cashup_deposit.cashup_main_balance += self.amount  # Add the amount to main balance
                    else:
                        # Deduct the whole cashup_owing_dps and add it to main balance
                        cashup_deposit.cashup_main_balance += cashup_owing_deposit.cashup_owing_dps
                        remaining_amount = self.amount - cashup_owing_deposit.cashup_owing_dps

                        # Now, deduct from cashup_owing_main_balance
                        if remaining_amount <= cashup_owing_deposit.cashup_owing_main_balance:
                            cashup_owing_deposit.cashup_owing_main_balance -= remaining_amount
                            self.buyer.main_balance += remaining_amount  # Add the remaining amount to buyer's main balance
                        else:
                            # If remaining amount is greater than cashup_owing_main_balance
                            self.buyer.main_balance += (remaining_amount - cashup_owing_deposit.cashup_owing_main_balance)
                            cashup_owing_deposit.cashup_owing_main_balance = Decimal('0.00')

                        # Set cashup_owing_dps to 0 since it's fully used
                        cashup_owing_deposit.cashup_owing_dps = Decimal('0.00')

                else:
                    # If cashup_owing_main_balance is not positive, add the amount directly to the buyer's main_balance
                    self.buyer.main_balance += self.amount


                # Save the updated deposit balances and buyer's main_balance
                cashup_owing_deposit.save()
                cashup_deposit.save()
                self.buyer.save()



                # Save the updated deposit balances and buyer's main_balance
                

        super().save(*args, **kwargs)

    def __str__(self):
            return f"{self.phone_number} - {self.buyer.name}"  # Assuming 'name' is an attribute of the 'Buyer' model.


  # Save the transaction itself  # Save the transaction itself # Save the transaction itself

from django.db import models
from django.conf import settings

class TransferHistory(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    verified=models.BooleanField(default=False)
    cashup_owing_deposit = models.ForeignKey('CashupOwingDeposit', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.buyer.username} - {self.amount} on {self.date}"
    def save(self, *args, **kwargs):
        # Check if the related CashupOwingDeposit has a requested_cashup_owing_main_balance of 0
        if self.cashup_owing_deposit and self.cashup_owing_deposit.requested_cashup_owing_main_balance == 0:
            self.verified = True
        super().save(*args, **kwargs)


class TransferHistoryofCashup(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    
    def save(self, *args, **kwargs):
        # Remove microseconds before saving the timestamp
        if self.date:
            self.date = self.date.replace(second=0,microsecond=0)
        super().save(*args, **kwargs)

    

    def __str__(self):
        return f"{self.buyer.username} - {self.amount} on {self.date}"
class TransferHistoryofCashupOwingDPS(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)

    
    def save(self, *args, **kwargs):
        # Remove microseconds before saving the timestamp
        if self.date:
            self.date = self.date.replace(second=0,microsecond=0)
        super().save(*args, **kwargs)

    

    def __str__(self):
        return f"{self.buyer.username} - {self.amount} on {self.date}"
    
class Slider(models.Model):
    title=models.CharField(max_length=20)
    image=models.CharField(max_length=500, blank=True, null=True, help_text="Image of the product")



class CashupProfitHistory(models.Model):
    cashup_deposit = models.ForeignKey(CashupDeposit, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=255)
    previous_value = models.DecimalField(max_digits=10, decimal_places=2)
    new_value = models.DecimalField(max_digits=10, decimal_places=2)
    updated_by = models.ForeignKey(Buyer, on_delete=models.SET_NULL, null=True, blank=True)  # User who made the change
    change_timestamp = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        # Remove microseconds before saving the timestamp
        if self.cashup_deposit and not self.updated_by:
            self.updated_by = self.cashup_deposit.buyer

        if self.change_timestamp:
            self.change_timestamp = self.change_timestamp.replace(second=0,microsecond=0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Change in {self.field_name} for CashupDeposit {self.cashup_deposit.id} on {self.change_timestamp}"
    

class CashupOwingProfitHistory(models.Model):
    cashup_owing_deposit = models.ForeignKey(CashupOwingDeposit, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=255)
    previous_value = models.DecimalField(max_digits=10, decimal_places=2)
    new_value = models.DecimalField(max_digits=10, decimal_places=2)
    updated_by = models.ForeignKey(Buyer, on_delete=models.SET_NULL, null=True, blank=True)  # User who made the change
    change_timestamp = models.DateTimeField(default=timezone.now)
    
    

    def save(self, *args, **kwargs):
        # Remove microseconds before saving the timestamp
        if self.cashup_owing_deposit and not self.updated_by:
            self.updated_by = self.cashup_owing_deposit.buyer

        if self.change_timestamp:
            self.change_timestamp = self.change_timestamp.replace(second=0,microsecond=0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Change in {self.field_name} for CashupDeposit {self.cashup_owing_deposit.id} on {self.change_timestamp}"



    
    
class CheckoutDetail(models.Model):
    purchase=models.ForeignKey(Purchase,on_delete=models.CASCADE)
    name=models.CharField(max_length=20)
    email=models.EmailField()
    address=models.CharField(max_length=100)
    city=models.CharField(max_length=20)
    postal_code=models.CharField(max_length=6)

    def __str__(self):
        return f"{self.name}"


# Signal to create Buyer when User is created
# Signal to create Buyer and Cashup deposits when User is created


from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from .models import Buyer, CashupOwingDeposit, CashupDeposit
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_buyer(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():  # Ensure atomic transactions
            phone_number = instance.username if instance.username else ''

            # Create Buyer
            buyer = Buyer.objects.create(
                user=instance,
                name=f"{instance.first_name} {instance.last_name}",
                phone_number=phone_number,
                address='',
                membership_status=False
            )

            # Manually save Buyer to ensure it has a valid primary key (pk)
            buyer.save()

            # Create CashupOwingDeposit with 0 initial balance
            cashup_owing_deposit = CashupOwingDeposit.objects.create(
                buyer=buyer,
                cashup_owing_main_balance=Decimal('0.00'),
                requested_cashup_owing_main_balance=Decimal('0.00'),
                verified=False
            )

            # Create CashupDeposit with 0 initial balance
            cashup_deposit = CashupDeposit.objects.create(
                buyer=buyer,
                cashup_main_balance=Decimal('0.00')
            )

            # Ensuring the related objects are saved
            cashup_owing_deposit.save()
            cashup_deposit.save()
            
            # We do not need to call `buyer.save()` again because the Buyer was already saved in the `create()` method

            # All changes are saved and committed by the transaction.atomic() context



from django.db.models.signals import pre_save

@receiver(pre_save, sender=CashupDeposit)
def track_profit_changes(sender, instance, **kwargs):
    # Fetch the previous state of the object if it's an update
    if instance.id:
        try:
            previous_instance = CashupDeposit.objects.get(id=instance.id)
        except CashupDeposit.DoesNotExist:
            previous_instance = None
    else:
        previous_instance = None  # New instance, no previous state

    # List of profit-related fields to track
    profit_fields = [
        'daily_profit', 'compounding_profit', 'monthly_profit', 'product_profit', 
        'daily_compounding_profit', 'monthly_compounding_profit'
    ]

    # If previous instance exists, check for differences
    if previous_instance:
        for field in profit_fields:
            previous_value = getattr(previous_instance, field, 0)
            new_value = getattr(instance, field, 0)

            # If the value has changed, log it in the ProfitHistory
            if previous_value != new_value:
                CashupProfitHistory.objects.create(
                    cashup_deposit=instance,
                    field_name=field,
                    previous_value=previous_value,
                    new_value=new_value,
                    updated_by=instance.updated_by,  # Capture who made the change
                )
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import CashupOwingDeposit, CashupOwingProfitHistory

@receiver(pre_save, sender=CashupOwingDeposit)
def track_profit_changes(sender, instance, **kwargs):
    # Fetch the previous state of the object if it's an update
    if instance.id:
        try:
            previous_instance = CashupOwingDeposit.objects.get(id=instance.id)
        except CashupOwingDeposit.DoesNotExist:
            previous_instance = None
    else:
        previous_instance = None  # New instance, no previous state

    # List of profit-related fields to track
    profit_fields = [
        'daily_profit', 'compounding_profit', 'monthly_profit', 'product_profit',
        'daily_compounding_profit', 'monthly_compounding_profit'
    ]

    # If previous instance exists, check for differences
    if previous_instance:
        for field in profit_fields:
            previous_value = getattr(previous_instance, field, 0)
            new_value = getattr(instance, field, 0)

            # If the value has changed, log it in the ProfitHistory
            if previous_value != new_value:
                # Ensure updated_by is set
                updated_by_user = instance.updated_by if instance.updated_by else instance.user
                
                CashupOwingProfitHistory.objects.create(
                    cashup_owing_deposit=instance,
                    field_name=field,
                    previous_value=previous_value,
                    new_value=new_value,
                    updated_by=updated_by_user,  # Ensure updated_by is set to correct user
                )

@receiver(post_save, sender=CashupOwingDeposit)
def update_transferhistory_verified(sender, instance, created, **kwargs):
    # Check if the 'requested_cashup_owing_main_balance' has become 0
    if instance.requested_cashup_owing_main_balance == 0:
        # Get all TransferHistory objects related to this CashupOwingDeposit
        transfer_history_records = TransferHistory.objects.filter(cashup_owing_deposit=instance)

        # Update the 'verified' field for all related TransferHistory objects
        transfer_history_records.update(verified=True)






