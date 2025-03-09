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
    
    def __str__(self):
        return f"Withdrawal request by {self.buyer.name} for {self.amount} - {self.status}"
    

class WithdrawalFromMainBalance(models.Model):
    buyer = models.ForeignKey('Buyer', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending")
    
    def __str__(self):
        return f"Withdrawal request by {self.buyer.name} for {self.amount} - {self.status}"


class WithdrawalFromCashupBalance(models.Model):
    buyer = models.ForeignKey('Buyer', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending")
    
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
    discount_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True, editable=False)
    members_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    item_image = models.CharField(max_length=500, blank=True, null=True, help_text="Image of the product")

    def save(self, *args, **kwargs):
        if self.price is not None:
            if self.discount_rate is not None and self.discount_rate > 0:
                self.discount_price = self.price - (self.price * self.discount_rate / 100)
            else:
                self.discount_price = self.price
        
        super().save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        if self.item:
            item_price = self.item.price
            self.total_price = item_price * self.quantity

        if self.discount_rate > 0:
            self.discount_price = item_price - (item_price * (self.discount_rate / 100))
            self.discount_total_price = self.discount_price * self.quantity
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
    verified = models.BooleanField(default=False)

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

    def __str__(self):
        return f"Deposit: {self.cashup_main_balance} by {self.buyer.name if self.buyer else 'Unknown Buyer'}"


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

    def save(self, *args, **kwargs):
        if not self.buyer:
            raise ValueError("Buyer does not exist")

        with transaction.atomic():  # Ensure atomicity
            # Fetch or create CashupOwingDeposit for the buyer
            cashup_owing_deposit, _ = CashupOwingDeposit.objects.get_or_create(
                buyer=self.buyer,
                defaults={
                    'cashup_owing_main_balance': Decimal('0.00'),
                    'requested_cashup_owing_main_balance': Decimal('0.00'),
                    'verified': False,
                }
            )

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
                    if self.amount <= cashup_owing_deposit.cashup_owing_main_balance:
                        # Deduct from cashup_owing_main_balance and add to cashup_main_balance
                        cashup_owing_deposit.cashup_owing_main_balance -= self.amount
                        cashup_deposit.cashup_main_balance += self.amount
                    else:
                        # If the amount is greater than cashup_owing_main_balance
                        remaining_amount = self.amount - cashup_owing_deposit.cashup_owing_main_balance
                        cashup_deposit.cashup_main_balance += cashup_owing_deposit.cashup_owing_main_balance
                        cashup_owing_deposit.cashup_owing_main_balance = Decimal('0.00')

                        # Add the remaining amount to the buyer's main_balance
                        self.buyer.main_balance += remaining_amount
                else:
                    # If cashup_owing_main_balance is not positive, add the amount directly to the buyer's main_balance
                    self.buyer.main_balance += self.amount

                # Save the updated deposit balances and buyer's main_balance
                cashup_owing_deposit.save()
                cashup_deposit.save()
                self.buyer.save()

        super().save(*args, **kwargs)

    def __str__(self):
            return f"{self.phone_number} - {self.buyer.name}"  # Assuming 'name' is an attribute of the 'Buyer' model.


  # Save the transaction itself  # Save the transaction itself # Save the transaction itself


        
    
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
@receiver(post_save, sender=User)
def create_buyer(sender, instance, created, **kwargs):
    if created:
        phone_number = instance.username if instance.username else ''
        
        # Create Buyer
        buyer = Buyer.objects.create(
            user=instance,
            name=f"{instance.first_name} {instance.last_name}",
            phone_number=phone_number,
            address='',
            membership_status=False
        )

        # Create CashupOwingDeposit with 0 initial balance
        CashupOwingDeposit.objects.create(
            buyer=buyer,
            cashup_owing_main_balance=Decimal('0.00'),  # Initialize with 0 balance
            requested_cashup_owing_main_balance=Decimal('0.00'),
            verified=False
        )

        # Create CashupDeposit with 0 initial balance
        CashupDeposit.objects.create(
            buyer=buyer,
            cashup_main_balance=Decimal('0.00')  # Initialize with 0 balance

        )





