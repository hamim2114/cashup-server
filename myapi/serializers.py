import re  # Import the re module for regular expressions
from rest_framework import serializers
from .models import Purchase, Buyer, CashupOwingDeposit, Item,WithdrawalFromCashupBalance, CashupDeposit ,BuyerTransaction ,CheckoutDetail
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from datetime import date
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.validators import UniqueValidator
from .models import Buyer

# Custom ValidationError
class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

# Item Serializer
class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'name', 'description', 'is_available', 'price','members_price','item_image','discount_rate',]

# Buyer Serializer
class BuyerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buyer
        fields = ['id', 'name', 'phone_number','main_balance','date_of_birth','gender', 'membership_status','address', 'main_balance','buyer_image']

# Purchase Serializer
from rest_framework import serializers
from .models import Purchase, Item


class PurchaseSerializer(serializers.ModelSerializer):
    item = ItemSerializer()  # Serialize item details
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_total_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    class Meta:
        model = Purchase
        fields = ['id', 'item', 'quantity', 'total_price', 'discount_total_price', 'confirmed', 'paid']


# CashupOwingDeposit Serializer

  # Assuming you have an ItemSerializer
from rest_framework import serializers
from .models import Purchase, Item

class PurchaseProductSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())  # Expect only item ID
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, required=False)
    
    class Meta:
        model = Purchase
        fields = ['item', 'quantity', 'total_price', 'discount_total_price', 'confirmed']

    def validate(self, data):
        """
        Optionally, add additional validation if necessary.
        """
        # For example, validate that `quantity` is greater than 0
        if data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return data

    def create(self, validated_data):
        # Extract the item from the validated data
        item = validated_data['item']
        quantity = validated_data['quantity']

        # Calculate total price and discount total price
        total_price = item.price * quantity
        discount_total_price = item.discount_price * quantity if item.discount_price else total_price

        # Create the purchase for the logged-in user (buyer)
        purchase = Purchase.objects.create(
            item=item,
            quantity=quantity,
            total_price=total_price,
            discount_total_price=discount_total_price,
            buyer=self.context['request'].user,  # Automatically set the buyer from the authenticated user
            confirmed=validated_data['confirmed']
        )
        
        return purchase





class CashupOwingDepositSerializer(serializers.ModelSerializer):
    buyer = BuyerSerializer(read_only=True)  # Nested serializer for buyer (read-only)

    class Meta:
        model = CashupOwingDeposit
        fields = [
            'id',
            'requested_cashup_owing_main_balance',
            'cashup_owing_main_balance',  # Updated field name (from cashup_owing_main_balance)
            'buyer',
            'created_at',
            'daily_profit',
            'compounding_profit',
            'monthly_profit',
            'withdraw',
            'product_profit',
            'compounding_withdraw',
            'monthly_compounding_profit',
            'daily_compounding_profit',
        ]
        read_only_fields = ['created_at'] 

        
# CashupDeposit Serializer
class CashupDepositSerializer(serializers.ModelSerializer):
    buyer = BuyerSerializer(read_only=True)  # Nested serializer for buyer (read-only)

    class Meta:
        model = CashupDeposit
        fields = [
            'id',
            'cashup_main_balance',  # Updated field name (from cashup_owing_main_balance)
            'buyer',
            'created_at',
            'daily_profit',
            'compounding_profit',
            'monthly_profit',
            'withdraw',
            'product_profit',
            'compounding_withdraw',
            'monthly_compounding_profit',
            'daily_compounding_profit',
        ]
        read_only_fields = ['created_at']  # Automatically set by the model

# Password Validation
def validate_password(value):
    """
    Validate the password to ensure it meets the requirements.
    """
    print(f"Validating password: {value}")  # Debugging
    if len(value) != 6:
        raise ValidationError('Password must be exactly 6 characters long.')
    return value

# serializers.py
from rest_framework import serializers
from .models import BuyerTransaction
from decimal import Decimal

class BuyerTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerTransaction
        fields = ['transaction_id', 'phone_number', 'amount', 'method', 'verified']
    
    # Validate the amount field to ensure it's a positive decimal value
    def validate_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Amount must be a positive value.")
        return value
    
    # Optionally, you can override the `create()` method to handle any extra logic before saving
    def create(self, validated_data):
        # Optionally add extra logic before saving, such as calculating main balance or other operations
        return super().create(validated_data)



class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        required=False,  # Make username optional in API
        validators=[UniqueValidator(queryset=Buyer.objects.all(), message="Username already exists.")]
    )
    phone_number = serializers.CharField(
        required=True,
        validators=[UniqueValidator(queryset=Buyer.objects.all(), message="Phone number already exists.")]
    )
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Buyer
        fields = ('id', 'name', 'username', 'phone_number', 'password', 'confirm_password', 'buyer_image', 'gender', 'date_of_birth')

    def validate_password(self, value):
        """Validate password strength."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        """Ensure password and confirm_password match."""
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        """Create a new user and handle unique constraint errors."""
        try:
            validated_data.pop("confirm_password")  # Remove confirm_password before saving
            
            # Set username to phone_number if not provided
            username = validated_data.get("username", validated_data["phone_number"])

            user = Buyer.objects.create(
                name=validated_data["name"],
                username=username,
                phone_number=validated_data["phone_number"],
                buyer_image=validated_data.get("buyer_image"),
                gender=validated_data.get("gender"),
                date_of_birth=validated_data.get("date_of_birth"),
            )
            user.set_password(validated_data["password"])  # Hash password
            user.save()
            return user

        except Exception as e:
            raise serializers.ValidationError({"error": f"Failed to create user: {str(e)}"})



# Login Serializer
# serializers.py


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone_number = data.get("phone_number")
        password = data.get("password")

        # Try to find the buyer using the phone_number
        buyer = Buyer.objects.filter(phone_number=phone_number).first()
        if not buyer:
            raise serializers.ValidationError("Invalid phone number or password.")

        # Validate the password
        if not buyer.check_password(password):
            raise serializers.ValidationError("Invalid phone number or password.")

        return {
            "buyer": buyer
        }

        
# Update Buyer Profile Serializer
# serializers.py

class UpdateBuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buyer
        fields = ['name', 'phone_number', 'date_of_birth', 'gender', 'address', 'buyer_image', 'membership_status']
        read_only_fields = ['phone_number']  # Assuming phone_number should not be updated

# serializers.py



from rest_framework import serializers
from .models import BuyerOTP

class BuyerOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerOTP
        fields = ['buyer', 'otp', 'created_at', 'is_verified']

class CheckoutDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckoutDetail
        fields = ['name', 'email', 'address', 'city', 'postal_code']  # Removed 'purchase' field

    def create(self, validated_data):
        # Automatically assign the `purchase` field from the context
        user_purchase = self.context.get('purchase')  # Retrieve the purchase from the context
        if not user_purchase:
            raise ValidationError("No purchase found for the checkout.")
        
        # Add the purchase to the validated data
        validated_data['purchase'] = user_purchase
        
        # Create and return the CheckoutDetails instance
        return CheckoutDetail.objects.create(**validated_data)

# Deposit Serializer
class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

# Transfer Serializer
class TransferSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

from rest_framework import serializers
from .models import WithdrawalFromCashupBalance

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalFromCashupBalance
        fields = '__all__'
        read_only_fields = ('buyer',)  # Make the buyer field read-only

    def create(self, validated_data):
        # Set the buyer to the currently logged-in user
        validated_data['buyer'] = self.context['request'].user
        return super().create(validated_data)
    
from .models import WithdrawalFromMainBalance

class WithdrawalFromMainBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalFromMainBalance
        fields = '__all__'
        read_only_fields = ('buyer',)  # Make the buyer field read-only

    def create(self, validated_data):
        # Set the buyer to the currently logged-in user
        validated_data['buyer'] = self.context['request'].user
        return super().create(validated_data)
    

from .models import WithdrawalFromCompoundingProfit
class WithdrawalFromCompoundingProfitSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalFromCompoundingProfit
        fields = '__all__'
        read_only_fields = ('buyer',)  # Make the buyer field read-only

    def create(self, validated_data):
        # Set the buyer to the currently logged-in user
        validated_data['buyer'] = self.context['request'].user
        return super().create(validated_data)

