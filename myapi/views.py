from rest_framework import viewsets , generics , mixins
from .models import Purchase, Buyer ,Item , CashupOwingDeposit ,CashupDeposit
from .serializers import PurchaseSerializer,ItemSerializer,RegisterSerializer, LoginSerializer,BuyerTransactionSerializer,TransferSerializer,CashupDepositSerializer,DepositSerializer ,BuyerSerializer , CashupOwingDepositSerializer ,DepositSerializer
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import UpdateBuyerProfileSerializer
from django.shortcuts import get_object_or_404
from django.db import transaction 
from rest_framework_simplejwt.tokens import RefreshToken



# Create your views here.
class ProductView(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `retrieve`, `create`, `update`, and `destroy` actions.
    """
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer

class BuyerView(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    """
    This viewset automatically provides `list`, `retrieve`, `create`, `update`, and `destroy` actions.
    """
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer
class ItemView(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `retrieve`, `create`, `update`, and `destroy` actions.
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializer


class CartedProductDelete(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can delete items

    def delete(self, request, pk, format=None):
        # Find the carted product based on the primary key (pk)
        try:
            carted_product = Purchase.objects.get(id=pk, buyer=request.user, confirmed=False)
        except Purchase.DoesNotExist:
            return Response({"detail": "Carted product not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Delete the product from the cart
        carted_product.delete()

        return Response({"detail": "Carted product successfully deleted."}, status=status.HTTP_204_NO_CONTENT)



class ConfirmedProductsList(generics.ListAPIView):
    # Set permission to ensure the user must be authenticated
    permission_classes = [IsAuthenticated]
    
    # Override the get_queryset method to filter by the authenticated user
    def get_queryset(self):
        # Get only confirmed purchases for the logged-in user
        return Purchase.objects.filter(buyer=self.request.user, confirmed=True).order_by('-id')
    
    # Define the serializer class
    serializer_class = PurchaseSerializer


class CartedProductsList(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access

    # Override the get_queryset method to filter purchases based on buyer and confirmed status
    def get_queryset(self):
        # Filter the purchases by the authenticated user and where confirmed is False
        return Purchase.objects.filter(buyer=self.request.user, confirmed=False).order_by('-id')

    # Specify the serializer class to format the response
    serializer_class = PurchaseSerializer


class ProductDetail(generics.RetrieveUpdateDestroyAPIView,mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    generics.GenericAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
class BuyerDetail(generics.RetrieveUpdateDestroyAPIView,mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer
    
    def get_object(self):
        # Get the authenticated user from the JWT token
        user = self.request.user
        
        # Retrieve the Buyer instance associated with the authenticated user
        buyer = get_object_or_404(Buyer, user=user)
        
        return buyer
    

class ConfirmedBuyerView(generics.ListAPIView):
    permission_classes=[IsAuthenticated]
    """
    This viewset provides `list`, `retrieve`, `create`, `update`, and `destroy` actions for confirmed buyers.
    """
    queryset = Buyer.objects.filter(purchase__confirmed=True).distinct()
    serializer_class = BuyerSerializer



class ConfirmedBuyersForProducts(APIView):
    permission_classes=[IsAuthenticated]
    """
    This view provides a list of all products with their confirmed buyers.
    """
    def get(self, request):
        # Fetch confirmed purchases and prefetch related buyers
        purchases = Purchase.objects.filter(confirmed=True).select_related('buyer')

        data = []
        for purchase in purchases:
            # Serialize the product (purchase)
            product_serializer = PurchaseSerializer(purchase)

            # Serialize the buyer (if exists) and exclude unwanted fields
            buyer_data = None
            if purchase.buyer:
                buyer_serializer = BuyerSerializer(purchase.buyer)
                buyer_data = buyer_serializer.data

                # Remove unwanted fields from the buyer data
                unwanted_fields = ['date_of_birth', 'gender']
                for field in unwanted_fields:
                    buyer_data.pop(field, None)  # Remove the field if it exists

            data.append({
                'product': product_serializer.data,
                'confirmed_buyer': buyer_data
            })

        return Response(data)

class BuyerPurchasesAPIView(APIView):
    permission_classes=[IsAuthenticated]

    """
    This view provides the purchased products for a specific buyer and calculates the discount prices and total cost.
    """
    def get(self, request, *args, **kwargs):
        buyer_id = kwargs.get('buyer_id')
        buyer = get_object_or_404(Buyer, id=request.user.id)
        products = Purchase.objects.filter(buyer=buyer, confirmed=True,paid=True)
        
        total_cost = 0
        product_list = []
        
        for product in products:
            original_price = product.total_price
            discount_rate = product.discount_rate
            quantity = product.quantity
            
            discount_price = original_price - (discount_rate * original_price / 100)
            total_cost += discount_price * quantity
            
            product_data = {
                'quantity': quantity,
                'product': PurchaseSerializer(product).data,
                'original_price': original_price,
                'discount_rate': discount_rate,
                'discount_price': discount_price,
                'total_cost': discount_price * quantity
            }
            product_list.append(product_data)
        
        response_data = {
            'buyer': BuyerSerializer(buyer).data,
            'products': product_list,
            'total_cost': total_cost
        }
        
        return Response(response_data)
from django.db.models import Prefetch
from rest_framework import generics
from .models import CashupOwingDeposit, Buyer
from .serializers import CashupOwingDepositSerializer
import logging

logger = logging.getLogger(__name__)


from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Buyer, BuyerTransaction
from .serializers import BuyerTransactionSerializer

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Buyer, BuyerTransaction
from .serializers import BuyerTransactionSerializer
# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Buyer, BuyerTransaction
from .serializers import BuyerTransactionSerializer

# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Buyer, BuyerTransaction
from .serializers import BuyerTransactionSerializer

class BuyerTransactionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Get the authenticated user
        user = request.user  # The logged-in user (assuming the buyer is the authenticated user)

        # Fetch the corresponding Buyer instance for the logged-in user
        try:
            buyer = Buyer.objects.get(username=user.username)  # Or use other unique identifiers like email
        except Buyer.DoesNotExist:
            return Response({"detail": "Buyer instance not found for this user."}, status=status.HTTP_400_BAD_REQUEST)

        # Add the 'buyer' field to the request data (this automatically sets the buyer's ID)
        request_data = request.data.copy()
        request_data['buyer'] = buyer.id  # Automatically set the buyer ID
        
        # Initialize the serializer with the request data
        serializer = BuyerTransactionSerializer(data=request_data)
        
        # Validate and save the transaction
        if serializer.is_valid():
            serializer.save(buyer=buyer)  # The buyer will automatically be saved through the serializer
            return Response(serializer.data, status=status.HTTP_201_CREATED)  # Return the created transaction data
        
        # If serializer is not valid, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)







    

class CashupOwingDepositByBuyerAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this view
    serializer_class = CashupOwingDepositSerializer

       
    def get_queryset(self):
        # Get the authenticated user from the JWT token
        buyer = self.request.user
        
        if not buyer:
            raise NotFound("Buyer not found.")
        
        return CashupOwingDeposit.objects.filter(buyer=buyer)
    
from rest_framework.permissions import AllowAny

class CashupDepositByBuyerAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this view
    serializer_class = CashupDepositSerializer

    def get_queryset(self):
        # Get the authenticated user from the JWT token
        buyer = self.request.user
        
        if not buyer:
            raise NotFound("Buyer not found.")
        
        # Retrieve the cashup deposits for this buyer
        return CashupDeposit.objects.filter(buyer=buyer)

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        # Instantiate the serializer with the incoming data
        serializer = RegisterSerializer(data=request.data)

        # Validate the data
        if serializer.is_valid():
            # Create a new Buyer instance and return it
            user = serializer.save()
            # Respond with the created user's data (excluding the password)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # If the data is not valid, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# --break-system-packages
# views.py

from django.contrib.auth import authenticate
from django.contrib.auth.models import User  # or your custom user model
from .serializers import LoginSerializer , CheckoutDetailsSerializer
# views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import LoginSerializer
from .models import Buyer
from rest_framework_simplejwt.tokens import RefreshToken

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        # Deserialize the request data
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            # Access the authenticated buyer object
            buyer = serializer.validated_data['buyer']

            # Generate JWT tokens
            refresh = RefreshToken.for_user(buyer)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Return a simplified response with just tokens and success message
            return Response({
                "detail": "Login successful!",
                "tokens": {
                    "access": access_token,
                    "refresh": refresh_token
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




# views.py
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import UpdateBuyerProfileSerializer
from .models import Buyer

class UpdateBuyerProfileAPIView(APIView):
    """
    API view for updating the Buyer profile.
    """
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view

    def put(self, request, *args, **kwargs):
        """
        Handle the PUT request to update the Buyer profile.
        """
        # The buyer is the authenticated user
        buyer = request.user  # Since the user is already a Buyer instance
        if not isinstance(buyer, Buyer):
            return Response(
                {"detail": "Buyer profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize the buyer instance with the incoming data
        serializer = UpdateBuyerProfileSerializer(buyer, data=request.data, partial=True)
        
        # Validate and save the serialized data
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Profile updated successfully."},
                status=status.HTTP_200_OK
            )
        
        # Return validation errors if there are any
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



    

from django.db.models import Sum
from django.db import transaction
from django.db.models import Sum


from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import Buyer
from .serializers import DepositSerializer
from decimal import Decimal

class DepositToMainBalance(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get the buyer instance associated with the authenticated user
        buyer = request.user  # Since request.user is already the Buyer (custom User model)
        
        # Validate the incoming data using the DepositSerializer
        serializer = DepositSerializer(data=request.data)

        if serializer.is_valid():
            # Convert the amount to Decimal
            amount = Decimal(serializer.validated_data['amount'])

            # Ensure that the deposit amount is positive
            if amount <= 0:
                return Response(
                    {"detail": "Amount must be greater than zero."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update the buyer's main balance
            buyer.main_balance += amount
            buyer.save()

            # Print the updated main balance for debugging
            print(f"New main balance: {buyer.main_balance}")

            # Return a success response
            return Response(
                {
                    "message": f"Deposited {amount} to main balance.",
                    "new_balance": float(buyer.main_balance),  # Convert Decimal to float for JSON serialization
                },
                status=status.HTTP_200_OK
            )
        
        # Return an error response if the serializer is not valid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import CashupDeposit

class TransferToCashupDeposit(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Use request.user directly since it's already the authenticated Buyer
        buyer = request.user

        # Refresh the buyer to ensure we get the latest data from the database
        buyer.refresh_from_db()

        # Serialize incoming data
        serializer = TransferSerializer(data=request.data)

        if serializer.is_valid():
            amount = serializer.validated_data['amount']

            # Log buyer's balance before transfer
            print(f"Buyer {buyer.id} initial balance: {buyer.main_balance}")

            # Check if buyer has enough funds in the main_balance
            if buyer.main_balance < amount:
                return Response(
                    {"error": "Insufficient funds"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Start a transaction to ensure atomicity
            with transaction.atomic():
                # Deduct the amount from the buyer's main_balance
                buyer.main_balance -= amount
                buyer.save()

                # Refresh the buyer again after saving to get updated balance
                buyer.refresh_from_db()

                # Log buyer's balance after deduction
                print(f"Buyer {buyer.id} updated balance: {buyer.main_balance}")

                # Try to retrieve the CashupDeposit entry for the buyer, handling multiple objects
                cashup_deposits = CashupDeposit.objects.filter(buyer=buyer)

                if cashup_deposits.exists():
                    # Update the cashup_main_balance of the first entry (or sum all entries if needed)
                    cashup_deposit = cashup_deposits.first()  # Or use any other way to select one
                    cashup_deposit.cashup_main_balance += amount
                    cashup_deposit.save()
                else:
                    # If no CashupDeposit exists, create one with the given amount
                    CashupDeposit.objects.create(
                        cashup_main_balance=amount,
                        buyer=buyer,
                    )

            # Return success response
            return Response(
                {
                    "message": f"Transferred {amount} to Cashup Deposit",
                    "balance": str(buyer.main_balance)  # Ensure balance is updated
                },
                status=status.HTTP_200_OK
            )

        # If serializer is invalid, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from .models import CashupOwingDeposit

from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

class TransferToCashupOwingDeposit(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        buyer = get_object_or_404(Buyer, id=request.user.id)
        serializer = TransferSerializer(data=request.data)

        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            
            with transaction.atomic():
                # Retrieve all CashupOwingDeposit instances for the buyer
                cashup_owing_deposits = CashupOwingDeposit.objects.filter(buyer=buyer)

                total_cashup_owing_main_balance = 0
                if cashup_owing_deposits.exists():
                    # Update the cashup_owing_main_balance for existing instances
                    for deposit in cashup_owing_deposits:
                        deposit.requested_cashup_owing_main_balance = deposit.requested_cashup_owing_main_balance + amount
                        deposit.save()
                        total_cashup_owing_main_balance = deposit.requested_cashup_owing_main_balance
                else:
                    # Create a new CashupOwingDeposit instance if none exist
                    cashup_owing_deposit = CashupOwingDeposit.objects.create(
                        requested_cashup_owing_main_balance=amount,
                        buyer=buyer,
                    )
                    total_cashup_owing_main_balance = cashup_owing_deposit.requested_ashup_owing_main_balance

            return Response({"message": f"Transferred {amount} to Requested Cashup Owing Deposit", "requested_cashup_owing_main_balance": total_cashup_owing_main_balance}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




from .serializers import PurchaseProductSerializer


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PurchaseProductSerializer
class PurchaseProduct(APIView):
    def post(self, request):
        serializer = PurchaseProductSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save()  # Save the purchase
            return Response({"message": "Purchase successful", "purchase": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# views.py
import random
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Buyer, BuyerOTP
from .serializers import BuyerOTPSerializer

class SendOTPToBuyer(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            buyer = Buyer.objects.get(phone_number=phone_number)
        except Buyer.DoesNotExist:
            return Response({'error': 'Buyer not found'}, status=status.HTTP_404_NOT_FOUND)

        otp = str(random.randint(100000, 999999))
        # Save OTP to database
        otp_instance = BuyerOTP.objects.create(buyer=buyer, otp=otp)

        # Send OTP via BulkSMS BD
        api_key = 'sZPisZCH9HlXyM4JpXeX'
        sender_id = 'Cashup'
        message = f'Your OTP is {otp}'
        url = f'http://bulksmsbd.net/api/smsapi?api_key={api_key}&type=text&number={phone_number}&senderid={sender_id}&message={message}'

        response = requests.get(url)
        if response.status_code == 200:
            return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class VerifyBuyerOTP(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')
        if not phone_number or not otp:
            return Response({'error': 'Phone number and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            buyer = Buyer.objects.get(phone_number=phone_number)
            otp_instance = BuyerOTP.objects.filter(buyer=buyer, otp=otp, is_verified=False).latest('created_at')
        except Buyer.DoesNotExist:
            return Response({'error': 'Buyer not found'}, status=status.HTTP_404_NOT_FOUND)
        except BuyerOTP.DoesNotExist:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        if otp_instance.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        otp_instance.is_verified = True
        otp_instance.save()

        return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)

from rest_framework.permissions import IsAuthenticated



from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Buyer, Purchase
from .serializers import BuyerSerializer, PurchaseSerializer
 # Assuming the 'Purchase' model is imported
from .serializers import CheckoutDetailsSerializer  # Assuming your serializer is imported


from .models import Buyer, Purchase
from .serializers import BuyerSerializer, PurchaseSerializer
 # Assuming the 'Purchase' model is imported
from .serializers import CheckoutDetailsSerializer  # Assuming your serializer is imported


class CheckoutDetailsView(APIView):
    def post(self, request, *args, **kwargs):
        # Retrieve all the unconfirmed purchases for the logged-in user
        user_purchases = Purchase.objects.filter(buyer=request.user, confirmed=False)

        # Handle the case where no unconfirmed purchases are found
        if not user_purchases:
            return Response({"detail": "No active unconfirmed purchases found."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Calculate the total price of all unconfirmed purchases
        total_price = sum([purchase.total_price for purchase in user_purchases])

        # Ensure the buyer has enough balance to complete the purchase
        if total_price > request.user.main_balance:
            return Response({"detail": "Insufficient balance to complete the purchase."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Use a transaction to ensure atomicity (both operations should succeed or fail together)
        with transaction.atomic():
            # Deduct the total price of all unconfirmed purchases from the buyer's main_balance
            request.user.main_balance -= total_price
            request.user.save()

            # Mark all the unconfirmed purchases as confirmed
            user_purchases.update(confirmed=True)

            # Pass the purchase to the serializer context for any related logic within the serializer
            serializer_data = []
            for purchase in user_purchases:
                serializer = CheckoutDetailsSerializer(data=request.data, context={'purchase': purchase})
                
                # Validate the serializer
                if serializer.is_valid():
                    # Save the CheckoutDetails
                    serializer.save()
                    serializer_data.append(serializer.data)
                else:
                    # If the serializer validation fails, rollback the transaction
                    transaction.set_rollback(True)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Return a success message with the serializer data
            return Response({
                "message": "All unconfirmed purchases successfully confirmed!",
                "purchase_details": serializer_data
            }, status=status.HTTP_201_CREATED)





class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Fetch the buyer instance associated with the authenticated user
        try:
            buyer = Buyer.objects.get(id=request.user.id)  # Query Buyer by the authenticated user's ID
        except Buyer.DoesNotExist:
            return Response(
                {"detail": "Buyer profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch purchases associated with the buyer (if any)
        purchases = Purchase.objects.filter(buyer=buyer)
        
        # Serialize the buyer profile and their purchases
        buyer_serializer = BuyerSerializer(buyer)
        purchase_serializer = PurchaseSerializer(purchases, many=True)

        # Combine the serialized data
        response_data = {
            "buyer": buyer_serializer.data,
            "purchases": purchase_serializer.data  # Include the list of purchases
        }

        return Response(response_data, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Purchase, Item


class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        # Try to fetch the unconfirmed purchase based on 'pk' (the purchase ID)
        user_purchase = Purchase.objects.filter(buyer=request.user, confirmed=False, id=pk)

        if not user_purchase:
            # No unconfirmed purchase found, create a new purchase for the user
            try:
                item = Item.objects.get(id=pk)  # Fetch the item from the database
            except Item.DoesNotExist:
                return Response(
                    {"detail": "Item not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Ensure item has a valid price
            if item.price is None:
                return Response(
                    {"detail": "Item price is not available."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if the user has a member price for this item (if applicable)
            member_price = self.get_member_price(request.user, item)
            if member_price and member_price != 0:
                # Use the member's price if it's set and not zero
                total_price = member_price
                discount_total_price = member_price  # If member price is used, no need for discount
            else:
                # Calculate the discount price if available
                discount_total_price = item.discount_price if item.discount_price else item.price
                total_price = item.price  # Regular price as fallback if no member price or discount

            # Create a new purchase with default quantity 1
            user_purchase = Purchase.objects.create(
                buyer=request.user,
                item=item,
                quantity=1,  # Default to 1, you can adjust as needed
                total_price=total_price,
                discount_rate=item.discount_rate,
                discount_total_price=discount_total_price,
                confirmed=False,  # Initially unconfirmed
            )

            # Proceed immediately with confirming the purchase and deducting the balance
            return self.confirm_purchase(user_purchase)

        # If an unconfirmed purchase is found, proceed with the logic
        return self.confirm_purchase(user_purchase)

    def get_member_price(self, user, item):
        """
        Fetch the member-specific price for the item.
        You can implement the logic based on how member prices are stored.
        For now, assuming it's a field in the `Item` model or related to the user.
        """
        # For example, let's assume `user.member_price` holds the member price for items.
        # You might need to adjust this logic based on how your system stores member prices.
        # This is a placeholder for actual logic you would use to fetch member-specific prices.

        # If the user has a member price set for this item, return it. Otherwise, return None.
        return getattr(user, "member_price", 0)  # Replace with actual logic

    def confirm_purchase(self, user_purchase):
        # Ensure that the purchase has a valid price before proceeding
        if user_purchase.discount_total_price is None or user_purchase.discount_total_price <= 0:
            return Response(
                {"detail": "Invalid total price for the purchase."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the user has sufficient balance
        if user_purchase.buyer.main_balance >= user_purchase.discount_total_price:
            # Deduct the balance from the user's account
            user_purchase.buyer.main_balance -= user_purchase.discount_total_price
            user_purchase.buyer.save()  # Save the updated balance

            # Confirm the purchase (set 'confirmed' and 'paid' to True)
            user_purchase.confirmed = True
            user_purchase.paid = True
            user_purchase.save()  # Save the updated purchase

            # Optionally, handle removing the item from the cart here, if applicable
            # (e.g., delete from cart or mark as purchased in another model)

            return Response(
                {
                    "detail": "Purchase confirmed and processed successfully.",
                    "updated_balance": str(user_purchase.buyer.main_balance),  # Show updated balance
                },
                status=status.HTTP_200_OK
            )
        else:
            # If the buyer does not have sufficient funds
            return Response(
                {"detail": "Insufficient balance to confirm purchase."},
                status=status.HTTP_400_BAD_REQUEST
            )




from .serializers import WithdrawalRequestSerializer
from .models import WithdrawalFromCashupBalance


class WithdrawalRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        List all withdrawal requests for the logged-in user.
        """
        withdrawal_requests = WithdrawalFromCashupBalance.objects.filter(buyer=request.user).order_by('-id')
        serializer = WithdrawalRequestSerializer(withdrawal_requests, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create a new withdrawal request for the logged-in user.
        """
        serializer = WithdrawalRequestSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from .models import WithdrawalFromMainBalance
from .serializers import WithdrawalFromMainBalanceSerializer
    
class WithdrawalRequestFromMianBalanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        List all withdrawal requests for the logged-in user.
        """
        withdrawal_requests = WithdrawalFromMainBalance.objects.filter(buyer=request.user).order_by('-id')
        serializer = WithdrawalFromMainBalanceSerializer(withdrawal_requests, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create a new withdrawal request for the logged-in user.
        """
        serializer = WithdrawalFromMainBalanceSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from .models import WithdrawalFromCompoundingProfit
from .serializers import WithdrawalFromCompoundingProfitSerializer
    
class WithdrawalRequestFromCompoundingProfitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        List all withdrawal requests for the logged-in user.
        """
        withdrawal_requests = WithdrawalFromCompoundingProfit.objects.filter(buyer=request.user).order_by('-id')
        serializer = WithdrawalFromCompoundingProfitSerializer(withdrawal_requests, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create a new withdrawal request for the logged-in user.
        """
        serializer = WithdrawalFromCompoundingProfitSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)









