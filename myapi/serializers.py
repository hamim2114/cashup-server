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
    category = serializers.StringRelatedField()

    class Meta:
        model = Item
        fields = ['id', 'name', 'description', 'is_available', 'price','category','members_price','item_image','discount_price']

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
        fields = ['id', 'item', 'quantity', 'total_price', 'discount_total_price', 'total_membership_price','confirmed', 'paid']

from rest_framework import serializers
from .models import TransferHistory , TransferHistoryofCashup 

class TransferHistorySerializer(serializers.ModelSerializer):
    date=serializers.DateTimeField(format="%Y-%m-%d %H:%M")


    
    class Meta:
        model = TransferHistory
        fields = ['buyer', 'amount', 'date','verified']  # Fields you want to expose


class TransferHistoryofCashupSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        # Get the original representation from the model serializer
            representation = super().to_representation(instance)
        
        # Format the date manually in the desired format
            if 'date' in representation:
                representation['date'] = instance.date.strftime("%Y-%m-%d %H:%M")

            return representation
    
    class Meta:
        model = TransferHistoryofCashup
        fields = ['buyer', 'amount', 'date']  # Fields you want to expose

        

    




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
            'cashup_owing_main_balance',
            'cashup_owing_dps',  # Updated field name (from cashup_owing_main_balance)
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
    date=serializers.DateTimeField(format="%Y-%m-%d %H:%M",read_only=True)
    class Meta:
        model = BuyerTransaction
        fields = ['transaction_id', 'phone_number', 'amount', 'method', 'verified','date']
    
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
from rest_framework import serializers

class TransferSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    verified = serializers.BooleanField(required=False) # Assuming 'verified' is a boolean field

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

    def to_representation(self, instance):
        """Override to exclude 'buyer' from API response."""
        representation = super().to_representation(instance)
        representation.pop('buyer', None)  # Remove the 'buyer' field from the response
        return representation

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

    
    def to_representation(self, instance):
        """Override to exclude 'buyer' from API response."""
        representation = super().to_representation(instance)
        representation.pop('buyer', None)  # Remove the 'buyer' field from the response
        return representation

    def create(self, validated_data):
        # Set the buyer to the currently logged-in user
        validated_data['buyer'] = self.context['request'].user
        return super().create(validated_data)


from .models import Slider , CashupProfitHistory ,CashupOwingProfitHistory

class CashupProfitHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CashupProfitHistory
        fields = ['field_name','previous_value', 'new_value','change_timestamp']

    # Optionally format the timestamp to display only date and time up to minute
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Format change_timestamp to display only date and time up to minute (no seconds or microseconds)
        representation['change_timestamp'] = instance.change_timestamp.strftime('%Y-%m-%d %H:%M')
        return representation
    

class CashupOwingProfitHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CashupOwingProfitHistory
        fields = ['field_name','previous_value', 'new_value', 'change_timestamp']

    # Optionally format the timestamp to display only date and time up to minute
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Format change_timestamp to display only date and time up to minute (no seconds or microseconds)
        representation['change_timestamp'] = instance.change_timestamp.strftime('%Y-%m-%d %H:%M')
        return representation


class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model=Slider
        fields='__all__'

    

from .models import WithdrawalFromCompoundingProfit
class WithdrawalFromCompoundingProfitSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalFromCompoundingProfit
        fields = '__all__'
        read_only_fields = ('buyer',)  # Make the buyer field read-only

    def to_representation(self, instance):
        """Override to exclude 'buyer' from API response."""
        representation = super().to_representation(instance)
        representation.pop('buyer', None)  # Remove the 'buyer' field from the response
        return representation

    def create(self, validated_data):
        # Set the buyer to the currently logged-in user
        validated_data['buyer'] = self.context['request'].user
        return super().create(validated_data)


from django.core.exceptions import ValidationError
from .models import BuyerOTP



class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        # Here, you can add additional validation to check if the phone number is valid.
        # For example, you can check if it contains only digits or follows a specific pattern.
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        return value

  
from django.utils import timezone
from datetime import timedelta

class ResetPasswordSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=5)

    def validate_otp(self, value):
        """
        Validate OTP and check if it's valid and not expired.
        """
        try:
            otp_entry = BuyerOTP.objects.get(otp=value, is_verified=False)
        except BuyerOTP.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP.")

        # Check if the OTP has expired (for example, after 5 minutes)
        if otp_entry.created_at + timedelta(minutes=5) < timezone.now():
            raise serializers.ValidationError("OTP has expired. Please request a new one.")

        return value

    def validate_new_password(self, value):
        """
        Validate the new password (you can add more validation rules here).
        """
        if len(value) < 5:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

