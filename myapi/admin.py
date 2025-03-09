from django.contrib import admin
from .models import Purchase, Buyer ,WithdrawalFromCashupBalance, WithdrawalFromCompoundingProfit,WithdrawalFromMainBalance,Category ,Item ,CheckoutDetail,CashupOwingDeposit , CashupDeposit , BuyerTransaction
from .models import User
from django.contrib import messages
from django.utils.translation import gettext_lazy as _  # Import for translation support

# Register your models here.
class BuyerAdmin(admin.ModelAdmin):
    search_fields=['phone_number']
class ItemAdmin(admin.ModelAdmin):
    search_fields=['name']
class PurchaseAdmin(admin.ModelAdmin):
    search_fields=['phone_number']
    readonly_fields = ['total_price']
    
class CashupAdmin(admin.ModelAdmin):
    search_fields=['phone_number']
class CategoryAdmin(admin.ModelAdmin):
    search_fields=['name']
class BuyerTransactionAdmin(admin.ModelAdmin):
    search_fields=['phone_number']
class CheckoutDetailsAdmin(admin.ModelAdmin):
    search_fields=['phone_number']
class CashupOwingDepositAdmin(admin.ModelAdmin):
    search_fields = ['buyer__phone_number']  # Ensure you search using the buyer's phone number
    list_display = ['buyer', 'cashup_owing_main_balance', 'requested_cashup_owing_main_balance', 'verified', 'created_at']

    def save_model(self, request, obj, form, change):
        # Check if the `verified` field is being set to True and `requested_cashup_owing_main_balance` is greater than 0
        if obj.verified and obj.requested_cashup_owing_main_balance > 0:
            try:
                # Ensure cashup_owing_main_balance is initialized (handle None/NULL case)
                if obj.cashup_owing_main_balance is None:
                    obj.cashup_owing_main_balance = 0  # Set default value if None

                # Add the requested balance to the cashup_owing_main_balance
                obj.cashup_owing_main_balance += obj.requested_cashup_owing_main_balance

                # Reset the requested cashup owing balance to 0
                obj.requested_cashup_owing_main_balance = 0
                obj.verified = False
                obj.save()

                # After updating, check if the cashup_owing_main_balance is now 0, and reset `verified` to False if needed
                
                    

                # Save the changes
                
            except Exception as e:
                self.message_user(request, f"Error: {str(e)}", level="error")
        else:
            # If it's not verified or requested amount is 0, simply save the object
            super().save_model(request, obj, form, change)

from django.db import transaction
class WithdrawalRequestAdmin(admin.ModelAdmin):
    # Override the save_model method to handle logic for withdrawal requests
    def save_model(self, request, obj, form, change):
        # If the status is 'Approved', process the withdrawal request
        if obj.status == 'Approved':
            # Ensure the buyer has a related CashupDeposit
            if hasattr(obj.buyer, 'cashup_deposits'):
                # Get the first related CashupDeposit
                cashup_deposit = obj.buyer.cashup_deposits.first()

                if cashup_deposit:
                    # Check if the cashup deposit balance is sufficient
                    if cashup_deposit.cashup_main_balance >= obj.amount:
                        # Begin a transaction to ensure atomicity
                        with transaction.atomic():
                            # Deduct the amount from the cashup deposit
                            cashup_deposit.cashup_main_balance -= obj.amount
                            cashup_deposit.save()

                            # Add the withdrawal amount to the buyer's main_balance
                            obj.buyer.main_balance += obj.amount
                            obj.buyer.save()

                            cashup_deposit.withdraw += obj.amount  # Add this line to log the withdrawn amount
                            cashup_deposit.save()

                            # Optionally, log the transaction or handle any related models
                            # For example, you can log this in a transaction model or something similar
                            # You can also update any related fields here if needed.

                            # Ensure the withdrawal request is marked as processed
                            obj.save()

                    else:
                        # Instead of raising an error, display a message
                        messages.warning(request, _('Insufficient funds in cashup deposit. Withdrawal cannot be processed.'))
                        # Optionally, you could mark the request as "Failed" or "Rejected" here
                        obj.status = 'Rejected'
                        obj.save()
                else:
                    # If no cashup deposit is found, show a different message
                    messages.error(request, _('No cashup deposit found for the buyer. Withdrawal cannot be processed.'))
                    obj.status = 'Rejected'
                    obj.save()

from django.db import transaction  # Ensure this import is included

class WithdrawalFromMainBalanceAdmin(admin.ModelAdmin):
    # Override the save_model method to handle logic for withdrawal requests
    def save_model(self, request, obj, form, change):
        # If the status is 'Approved', process the withdrawal request
        if obj.status == 'Approved':
            # Ensure the buyer has a related CashupDeposit
            if hasattr(obj.buyer, 'cashup_deposits'):
                # Get the first related CashupDeposit
                cashup_deposit = obj.buyer.cashup_deposits.first()

                if Buyer:
                    # Check if the buyer's main balance is sufficient
                    if obj.buyer.main_balance >= obj.amount:
                        # Begin a transaction to ensure atomicity
                        with transaction.atomic():
                            # Deduct the amount from the buyer's main balance
                            obj.buyer.main_balance -= obj.amount
                            obj.buyer.save()

                            # Optionally, log the transaction or handle any related models
                            # For example, you can log this in a transaction model or something similar

                            # Ensure the withdrawal request is marked as processed
                            obj.save()

                    else:
                        # Instead of raising an error, display a message
                        messages.warning(request, _('Insufficient funds in your balance. Withdrawal cannot be processed.'))
                        # Optionally, you could mark the request as "Failed" or "Rejected" here
                        obj.status = 'Rejected'
                        obj.save()
                else:
                    # If no cashup deposit is found, show a different message
                    messages.error(request, _('No cashup deposit found for the buyer. Withdrawal cannot be processed.'))
                    obj.status = 'Rejected'
                    obj.save()


class WithdrawalFromCmpoundingProfitAdmin(admin.ModelAdmin):
    # Override the save_model method to handle logic for withdrawal requests
    def save_model(self, request, obj, form, change):
        # If the status is 'Approved', process the withdrawal request
        if obj.status == 'Approved':
            # Ensure the buyer has a related CashupDeposit
            if hasattr(obj.buyer, 'cashup_deposits'):
                # Get the first related CashupDeposit
                cashup_deposit = obj.buyer.cashup_deposits.first()

                if cashup_deposit:
                    # Check if the cashup deposit balance is sufficient
                    if cashup_deposit.compounding_profit >= obj.amount:
                        # Begin a transaction to ensure atomicity
                        with transaction.atomic():
                            # Deduct the amount from the cashup deposit
                            cashup_deposit.compounding_profit -= obj.amount
                            cashup_deposit.save()

                            # Add the withdrawal amount to the buyer's main_balance
                            obj.buyer.main_balance += obj.amount
                            obj.buyer.save()

                            cashup_deposit.compounding_withdraw += obj.amount  # Add this line to log the withdrawn amount
                            cashup_deposit.save()

                            # Optionally, log the transaction or handle any related models
                            # For example, you can log this in a transaction model or something similar
                            # You can also update any related fields here if needed.

                            # Ensure the withdrawal request is marked as processed
                            obj.save()

                    else:
                        # Instead of raising an error, display a message
                        messages.warning(request, _('Insufficient funds in cashup deposit compounding profit. Withdrawal cannot be processed.'))
                        # Optionally, you could mark the request as "Failed" or "Rejected" here
                        obj.status = 'Rejected'
                        obj.save()
                else:
                    # If no cashup deposit is found, show a different message
                    messages.error(request, _('No cashup deposit found for the buyer. Withdrawal cannot be processed.'))
                    obj.status = 'Rejected'
                    obj.save()



# Register the custom admin class
admin.site.register(CashupOwingDeposit, CashupOwingDepositAdmin)
admin.site.register(Purchase,PurchaseAdmin)
admin.site.register(Buyer,BuyerAdmin)
admin.site.register(Category,CategoryAdmin)
admin.site.register(Item,ItemAdmin)
admin.site.register(CashupDeposit,CashupAdmin)
admin.site.register(BuyerTransaction,BuyerTransactionAdmin)
admin.site.register(CheckoutDetail,CheckoutDetailsAdmin)
admin.site.register(WithdrawalFromMainBalance,WithdrawalFromMainBalanceAdmin)
admin.site.register(WithdrawalFromCashupBalance, WithdrawalRequestAdmin)
admin.site.register(WithdrawalFromCompoundingProfit,WithdrawalFromCmpoundingProfitAdmin)







