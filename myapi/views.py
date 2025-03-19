from rest_framework import viewsets , generics , mixins
from .models import Purchase, Buyer ,Item , CashupOwingDeposit ,CashupDeposit
from .serializers import PurchaseSerializer,ItemSerializer,RegisterSerializer, LoginSerializer,BuyerTransactionSerializer,TransferSerializer,CashupDepositSerializer,DepositSerializer ,BuyerSerializer , CashupOwingDepositSerializer ,DepositSerializer
from django.db.models import Prefetch
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import UpdateBuyerProfileSerializer
from django.shortcuts import get_object_or_404
from django.db import transaction 
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category


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

class ItemFilter(filters.FilterSet):
    category = filters.ModelChoiceFilter(queryset=Category.objects.all())  # Filter by category
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')  # Optional: Search by name

    class Meta:
        model = Item
        fields = ['category', 'name'] 
class ItemView(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `retrieve`, `create`, `update`, and `destroy` actions.
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = ItemFilter 
    filter_backends = (SearchFilter,)
    search_fields = ['name', 'description']


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
    

from rest_framework import generics
from .models import CashupProfitHistory ,CashupOwingProfitHistory
from .serializers import CashupProfitHistorySerializer , CashupOwingProfitHistorySerializer

class CashupProfitHistoryListView(generics.ListAPIView):
    permission_classes=[IsAuthenticated]
    serializer_class = CashupProfitHistorySerializer

    def get_queryset(self):
        # Filter only by the logged-in user (updated_by = request.user)
        return CashupProfitHistory.objects.filter(updated_by=self.request.user)

class CompoundingProfitHistoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CashupProfitHistorySerializer

    def get_queryset(self):
        # Filter by the logged-in user and the specific field_name
        return CashupProfitHistory.objects.filter(
            updated_by=self.request.user, field_name="compounding_profit"
        )


class CashupOwingProfitHistoryListView(generics.ListAPIView):
    permission_classes=[IsAuthenticated]
    serializer_class = CashupOwingProfitHistorySerializer

    def get_queryset(self):
        # Filter only by the logged-in user (updated_by = request.user)
        return CashupOwingProfitHistory.objects.filter(updated_by=self.request.user)


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
    def get(self, request, *args, **kwargs):
        user = request.user  # The logged-in user
        
        # Fetch the corresponding Buyer instance for the logged-in user
        try:
            buyer = Buyer.objects.get(username=user.username)
        except Buyer.DoesNotExist:
            return Response({"detail": "Buyer instance not found for this user."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch all transactions for this buyer
        transactions = BuyerTransaction.objects.filter(buyer=buyer).order_by('-date')  # Adjust field name if needed
        
        # Serialize the data
        serializer = BuyerTransactionSerializer(transactions, many=True)
        
        # Return the list of transactions
        return Response(serializer.data, status=status.HTTP_200_OK)







    

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


    def perform_update(self, serializer):
        # Automatically set the updated_by field to the current logged-in user before saving
        serializer.save(updated_by=self.request.user)

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

            CashupOwingDeposit.objects.create(
                    buyer=user,  # The user is the buyer
                    cashup_owing_main_balance=Decimal('0.00'),
                    requested_cashup_owing_main_balance=Decimal('0.00'),
                    verified=False
                )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        
        # If the data is not valid, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



from rest_framework.exceptions import NotFound
 # Ensure the user is authenticated
from .models import ReferralCode, Buyer

class ReferralCodeView(APIView):
    """
    API View to generate a new referral code with the logged-in user as the creator (Buyer).
    """
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        # Get the logged-in user (buyer)
        buyer = request.user

        # Ensure the user is a Buyer (you might want to confirm this based on your user model)
        if not isinstance(buyer, Buyer):
            return Response({'detail': 'User is not a valid Buyer.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if ReferralCode.objects.filter(creator=buyer).exists():
            return Response(
                {"detail": "You already have a referral code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a new referral code for the logged-in buyer (creator)
        referral_code = ReferralCode.objects.create(
            code=ReferralCode.generate_unique_code(),
            creator=buyer,  # The logged-in buyer is the creator of the referral code
            is_valid=True,  # Set valid as per business rules
        )

        return Response({
            'referral_code': referral_code.code,
            'message': 'Affliate code generated successfully'
        }, status=status.HTTP_201_CREATED)



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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import Buyer, BuyerOTP
from .serializers import ForgotPasswordSerializer
from django.utils import timezone
import random
import string

# Function to generate OTP
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    """
    API view to handle forgot password request for a buyer.
    This view will:
    - Validate the phone number.
    - Generate and save an OTP.
    - otp the OTP to the user's phone (not implemented here).
    """

    def post(self, request, *args, **kwargs):
        # Validate the phone number via the serializer
        serializer = ForgotPasswordSerializer(data=request.data)

        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']

            # Check if the buyer exists with the provided phone number
            try:
                buyer = Buyer.objects.get(phone_number=phone_number)
            except Buyer.DoesNotExist:
                return Response({"detail": "Buyer with this phone number does not exist."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate OTP
            otp = generate_otp()

            # Create a new OTP entry for the buyer
            otp_entry = BuyerOTP.objects.create(
                buyer=buyer,
                otp=otp,
                is_verified=False,
                created_at=timezone.now()
            )

            # Here, you would typically send the OTP to the user's phone number via SMS.
            # For now, we are just returning a response.
            # (Don't return the OTP in production, it's for testing only)
            return Response({
                "detail": "OTP has been sent to your phone.",
                # Remove the OTP in production!
                "otp": otp  # Only for testing
            }, status=status.HTTP_200_OK)

        # If the serializer is not valid, return the errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





from django.contrib.auth.hashers import make_password
from .models import Buyer, BuyerOTP
from django.utils import timezone
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.contrib.auth.hashers import make_password
from .models import BuyerOTP
from .serializers import ResetPasswordSerializer
from django.utils import timezone
from datetime import timedelta

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]  # You may want to restrict this based on your auth setup.

    """
    API view to verify OTP and reset password for the buyer.
    This view will:
    - Validate the OTP.
    - If valid and not expired, allow password reset and delete the old one.
    """
    def post(self, request, *args, **kwargs):
        # Use the serializer to validate the data
        serializer = ResetPasswordSerializer(data=request.data)

        # Validate the serializer fields
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get OTP and new password from validated data
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        # Verify the OTP
        try:
            otp_entry = BuyerOTP.objects.get(otp=otp, is_verified=False)
            buyer = otp_entry.buyer
        except BuyerOTP.DoesNotExist:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the OTP has expired (for example, after 5 minutes)
        if otp_entry.created_at + timedelta(minutes=5) < timezone.now():
            return Response({"detail": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark the OTP as verified
        otp_entry.is_verified = True
        otp_entry.save()

        # Hash and reset the password
        buyer.password = make_password(new_password)
        buyer.save()

        # Optionally, delete the OTP after successful password reset
        otp_entry.delete()

        return Response({"detail": "Password has been successfully reset."}, status=status.HTTP_200_OK)


from .models import CompanyNumber
from .serializers import CompanyNumberSerializer

class CompanyNumberListView(APIView):
    def get(self, request, *args, **kwargs):
        # Get all company numbers from the database
        company_numbers = CompanyNumber.objects.all()

        # Serialize the data
        serializer = CompanyNumberSerializer(company_numbers, many=True)

        # Return the serialized data in the response
        return Response(serializer.data, status=status.HTTP_200_OK)






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
from .models import CashupDeposit , TransferHistoryofCashup ,TransferHistoryofCashupOwingDPS

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


                TransferHistoryofCashup.objects.create(
                    buyer=buyer,
                    amount=amount,
                      # Assuming the 'method' is included in the serializer
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
    def get(self, request):
                # Get transfer history for the authenticated buyer (all history)
        buyer = request.user

                # Fetch all transfer history for the buyer
        transfers = TransferHistoryofCashup.objects.filter(buyer=buyer).order_by('-date')

                # Serialize the data
        transfer_data = [
                    {
                    "amount": str(transfer.amount),
                    "date": transfer.date,
                    
                    }
                for transfer in transfers
            ]

        return Response(transfer_data, status=status.HTTP_200_OK)


from .models import CashupOwingDeposit

from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware
from .models import CashupDeposit, TransferHistory 
from datetime import datetime
from .serializers import TransferHistorySerializer
class TransferToCashupOwingDeposit(APIView):
    permission_classes = [IsAuthenticated]
    from django.db import transaction
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Buyer, CashupOwingDeposit, TransferHistory
from .serializers import TransferSerializer

class TransferToCashupOwingDeposit(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        buyer = get_object_or_404(Buyer, id=request.user.id)
        serializer = TransferSerializer(data=request.data)

        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            verified = serializer.validated_data['verified']

            with transaction.atomic():
                # Retrieve all CashupOwingDeposit instances for the buyer
                cashup_owing_deposits = CashupOwingDeposit.objects.filter(buyer=buyer)

                total_cashup_owing_main_balance = Decimal(0)
                cashup_owing_deposit = None  # Initialize to None

                if cashup_owing_deposits.exists():
                    # Update the cashup_owing_main_balance for existing instances
                    for deposit in cashup_owing_deposits:
                        deposit.requested_cashup_owing_main_balance += amount
                        deposit.save()
                        total_cashup_owing_main_balance += deposit.requested_cashup_owing_main_balance

                    # Choose the first deposit as the cashup_owing_deposit
                    cashup_owing_deposit = cashup_owing_deposits.first()

                else:
                    # Create a new CashupOwingDeposit instance if none exist
                    cashup_owing_deposit = CashupOwingDeposit.objects.create(
                        requested_cashup_owing_main_balance=amount,
                        buyer=buyer,
                    )
                    total_cashup_owing_main_balance = cashup_owing_deposit.requested_cashup_owing_main_balance

                

                # Create TransferHistory and associate with CashupOwingDeposit
                TransferHistory.objects.create(
                    buyer=buyer,
                    amount=amount,
                    verified=verified,  # Assuming this is set based on your logic
                    cashup_owing_deposit=cashup_owing_deposit  # Link to the deposit
                )

            return Response({
                "message": f"Transferred {amount} to Requested Cashup Owing Deposit",
                "requested_cashup_owing_main_balance": total_cashup_owing_main_balance
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    
    def get(self, request):
                # Get transfer history for the authenticated buyer (all history)
        buyer = request.user

                # Fetch all transfer history for the buyer
        transfers = TransferHistory.objects.filter(buyer=buyer).order_by('-date')

                # Serialize the data
        transfer_data = [
                    {
                    "amount": str(transfer.amount),
                    "date": transfer.date,
                    "verified":transfer.verified,
                    
                    
                    
                    }
                for transfer in transfers
            ]

        return Response(transfer_data, status=status.HTTP_200_OK)
from decimal import Decimal



class TransferToCashupOwingDPSView(APIView):
    permission_classes = [IsAuthenticated]
      # Ensure the user is authenticated

    def post(self, request):
        buyer = request.user
        # Get the logged-in user
      

        # Get the CashupOwingDeposit object for the logged-in user
        try:
            cashup_owing_deposit = CashupOwingDeposit.objects.get(buyer=buyer)
        except CashupOwingDeposit.DoesNotExist:
            return Response({"error": "CashupOwingDeposit not found for the user."}, status=status.HTTP_404_NOT_FOUND)

        # Get the transfer amount from the request data
        amount = request.data.get('amount', None)
        if amount is None:
            return Response({"error": "Amount is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate amount
        try:
            amount = Decimal(amount)
        except ValueError:
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user cannot transfer more than the available balance
        if amount > cashup_owing_deposit.cashup_owing_main_balance:
            return Response({"error": "Amount exceeds available balance."}, status=status.HTTP_400_BAD_REQUEST)

        # Perform the transfer
        cashup_owing_deposit.cashup_owing_main_balance -= amount
        cashup_owing_deposit.cashup_owing_dps += amount
        cashup_owing_deposit.save()

        TransferHistoryofCashupOwingDPS.objects.create(
                    buyer=buyer,
                    amount=amount,
                      # Assuming the 'method' is included in the serializer
                )
        

        # Serialize the updated data and return response
        serializer = CashupOwingDepositSerializer(cashup_owing_deposit)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def get(self, request):
                # Get transfer history for the authenticated buyer (all history)
        buyer = request.user

                # Fetch all transfer history for the buyer
        transfers = TransferHistoryofCashupOwingDPS.objects.filter(buyer=buyer).order_by('-date')

                # Serialize the data
        transfer_data = [
                    {
                    "amount": str(transfer.amount),
                    "date": transfer.date,
                    
                    }
                for transfer in transfers
            ]

        return Response(transfer_data, status=status.HTTP_200_OK)





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
# views.py
import random
import os
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Buyer, BuyerOTP
from rest_framework.permissions import AllowAny


import logging
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class SendOTPToBuyer(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            logger.error('Phone number is required')
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            buyer = Buyer.objects.get(phone_number=phone_number)
        except Buyer.DoesNotExist:
            logger.error(f'Buyer not found for phone number: {phone_number}')
            return Response({'error': 'Buyer not found'}, status=status.HTTP_404_NOT_FOUND)

        otp = str(random.randint(100000, 999999))
        # Use timezone-aware datetime for expires_at
        expires_at = timezone.now() + timedelta(minutes=5)

        try:
            otp_instance = BuyerOTP.objects.create(buyer=buyer, otp=otp, expires_at=expires_at)
        except Exception as e:
            logger.exception('Error creating OTP instance')
            return Response({'error': 'An error occurred while creating OTP', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Continue with your code to send the OTP...

        # Send OTP via BulkSMS BD (example)
        api_key = os.getenv('BULKSMS_API_KEY', 'n2HH10dNkbbVeSB1TamR')  # Use environment variable for API key
        sender_id = os.getenv('BULKSMS_SENDER_ID', '8809617624800')  # Use environment variable for sender ID
        message = f'Your Cashup OTP is {otp}'

        # URL encode the message to handle special characters
        encoded_message = quote_plus(message)

        params = {
            'api_key': api_key,
            'type': 'text',
            'number': phone_number,
            'senderid': sender_id,
            'message': encoded_message
        }
        url = f'http://bulksmsbd.net/api/smsapi?{urlencode(params)}'

        try:
            response = requests.get(url)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status_code') == 202:
                    return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)
                else:
                    error_code = response_data.get('status_code', 'Unknown')
                    error_message = self.get_error_message(error_code)
                    return Response({'error': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({'error': 'Failed to send OTP, please try again later'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except requests.RequestException as e:
            logger.exception('Error sending OTP request')
            return Response({'error': 'An error occurred while sending OTP', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_error_message(self, error_code):
        error_messages = {
            202: 'SMS submitted successfully.',
            1001: 'Invalid number.',
            1002: 'Sender ID is incorrect or disabled.',
            1003: 'Required fields are missing.',
            1005: 'Internal error.',
            1006: 'Balance validity not available.',
            1007: 'Balance insufficient.',
            1011: 'User ID not found.',
            1012: 'Masking SMS must be in Bengali.',
            1013: 'Sender ID not found in the gateway for the provided API key.',
            1014: 'Sender type name not found.',
            1015: 'Sender ID does not have a valid gateway.',
            1016: 'Sender type name active price info not found.',
            1017: 'Sender type name price info not found.',
            1018: 'Account is disabled.',
            1019: 'Sender type name price for this account is disabled.',
            1020: 'Parent account not found.',
            1021: 'Parent account sender type name not found.',
            1031: 'Account not verified.',
            1032: 'IP is not whitelisted.',
        }
        return error_messages.get(error_code, 'Unknown error occurred')



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


from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
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

        # Retrieve the user's cashup balance
        cashup_balance = request.user.cashup_deposits.first().cashup_main_balance  # Fetching the user's main cashup balance

        # Retrieve the user's main balance
        main_balance = request.user.main_balance

        # Determine the price to charge the buyer
        if cashup_balance > 0:
            # If the total price is less than or equal to the cashup balance
            if total_price <= cashup_balance:
                # Apply the member price (total_price) to the purchase
                total_member_price = sum([purchase.membership_price * purchase.quantity for purchase in user_purchases])

                # Deduct the total member price from the main balance (buyer pays the member price)
                if total_member_price > main_balance:
                    return Response({"detail": "Insufficient balance to complete the purchase."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Deduct full member price from the main balance
                request.user.main_balance -= total_member_price
                request.user.save()

            else:
                # If the total price is greater than the cashup balance, use the full original price
                if total_price > main_balance:
                    return Response({"detail": "Insufficient balance to complete the purchase."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Deduct full original price (total price) from the main balance
                request.user.main_balance -= total_price
                request.user.save()

        else:
            # No cashup balance, deduct full price from the main balance
            if total_price > main_balance:
                return Response({"detail": "Insufficient balance to complete the purchase."},
                                 status=status.HTTP_400_BAD_REQUEST)

            # Deduct full price from main balance
            request.user.main_balance -= total_price
            request.user.save()

        # Mark all the unconfirmed purchases as confirmed
        user_purchases.update(confirmed=True)

        # Return a success message
        return Response({
            "message": "All unconfirmed purchases successfully confirmed!",
        }, status=status.HTTP_201_CREATED)





from .models import Slider
from .serializers import SliderSerializer

class SliderCreateView(APIView):
    def get(self, request, *args, **kwargs):
        # Retrieve all slider data
        sliders = Slider.objects.all()  # You can apply filters if needed
        
        # Serialize the data
        serializer = SliderSerializer(sliders, many=True)
        
        # Return serialized data as response
        return Response(serializer.data, status=status.HTTP_200_OK)
    


from .models import SponsoredBy
from .serializers import SponseredBySerializer

class SponsoredByCreateView(APIView):
    def get(self, request, *args, **kwargs):
        # Retrieve all slider data
        sliders = SponsoredBy.objects.all()  # You can apply filters if needed
        
        # Serialize the data
        serializer = SponseredBySerializer(sliders, many=True)
        
        # Return serialized data as response
        return Response(serializer.data, status=status.HTTP_200_OK)


from .models import ReferralCode
from .serializers import ReferralCodeSerializer

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Buyer, Purchase
from .serializers import BuyerSerializer, PurchaseSerializer

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
            "purchases": purchase_serializer.data,  # Include the list of purchases
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
    

from .models import CashupDepositHistory
from .serializers import CashupDepositHistorySerializer
    
class CashupDepositHistoryView(generics.ListAPIView):
    serializer_class = CashupDepositHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Get the logged-in user's cashup deposit history
        return CashupDepositHistory.objects.filter(updated_by=self.request.user)
    
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

from .models import WithdrawalFromDailyProfit
from .serializers import WithdrawalFromDailyProfitSerializer

class WithdrawalRequestFromDailyProfitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        List all withdrawal requests for the logged-in user from daily profit.
        """
        # Get all withdrawal requests for the logged-in user, ordered by most recent
        withdrawal_requests = WithdrawalFromDailyProfit.objects.filter(buyer=request.user).order_by('-date')
        
        # Serialize the data
        serializer = WithdrawalFromDailyProfitSerializer(withdrawal_requests, many=True)
        
        # Return the serialized data in the response
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create a new withdrawal request for the logged-in user from daily profit.
        """
        # Pass request context for the serializer (which can be used to reference the logged-in user)
        serializer = WithdrawalFromDailyProfitSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # Save the withdrawal request
            serializer.save()

            # Return the created withdrawal request in the response with a 201 status code
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # If serializer is invalid, return errors with a 400 status code
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .models import WithdrawalFromAffiliateProfit
from .serializers import WithdrawalFromAffiliateProfitSerializer


class WithdrawalRequestFromAffiliateProfitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        List all withdrawal requests for the logged-in user from affiliate profit.
        """
        # Get all withdrawal requests for the logged-in user, ordered by most recent
        withdrawal_requests = WithdrawalFromAffiliateProfit.objects.filter(buyer=request.user).order_by('-date')
        
        # Serialize the data
        serializer = WithdrawalFromAffiliateProfitSerializer(withdrawal_requests, many=True)
        
        # Return the serialized data in the response
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create a new withdrawal request for the logged-in user from affiliate profit.
        """
        # Pass request context for the serializer (which can be used to reference the logged-in user)
        serializer = WithdrawalFromAffiliateProfitSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # Save the withdrawal request
            serializer.save()

            # Return the created withdrawal request in the response with a 201 status code
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # If serializer is invalid, return errors with a 400 status code
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from itertools import chain
from .models import (
    WithdrawalFromCompoundingProfit,
    WithdrawalFromMainBalance,
    WithdrawalFromCashupBalance,
    WithdrawalFromDailyProfit,
    WithdrawalFromAffiliateProfit
)
from .serializers import WithdrawalSerializer

class WithdrawalHistoryView(APIView):
    def get(self, request, *args, **kwargs):
        # Fetch all withdrawal records from different models
        compounding_withdrawals = WithdrawalFromCompoundingProfit.objects.all()
        main_balance_withdrawals = WithdrawalFromMainBalance.objects.all()
        cashup_withdrawals = WithdrawalFromCashupBalance.objects.all()
        daily_profit_withdrawals = WithdrawalFromDailyProfit.objects.all()
        affiliate_profit_withdrawals = WithdrawalFromAffiliateProfit.objects.all()

        # Merge all the withdrawal querysets
        all_withdrawals = list(chain(
            compounding_withdrawals,
            main_balance_withdrawals,
            cashup_withdrawals,
            daily_profit_withdrawals,
            affiliate_profit_withdrawals
        ))

        # Sort all withdrawals by date in descending order
        sorted_withdrawals = sorted(all_withdrawals, key=lambda x: x.date, reverse=True)

        # Serialize the withdrawals
        serializer = WithdrawalSerializer(sorted_withdrawals, many=True)

        # Return the serialized data
        return Response(serializer.data, status=status.HTTP_200_OK)

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # IsAuthenticated permission
from rest_framework.views import APIView
from .serializers import ChangePasswordSerializer


class ChangePasswordView(APIView):
    def post(self, request, *args, **kwargs):
        # Initialize the serializer with data from the request
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        # Validate the data
        if not serializer.is_valid():
            # Return validation errors as response
            return Response({
                "error": "Validation failed",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Call the save method, which may return a success or error response
        save_result = serializer.save()

        # If the response contains an error
        if "error" in save_result:
            return Response({
                "error": save_result["error"]
            }, status=status.HTTP_400_BAD_REQUEST)

        # If the response contains a success message
        return Response({
            "message": save_result["success"]
        }, status=status.HTTP_200_OK)



class ReferralGetCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Fetch all referral codes associated with the authenticated user
        referral_codes = ReferralCode.objects.filter(creator=request.user)

        # Serialize the referral codes
        serializer = ReferralCodeSerializer(referral_codes, many=True)

        # Return the serialized data
        return Response(serializer.data, status=status.HTTP_200_OK)
    
from .serializers import ProductAdSliderSerializer
from .models import ProductAdSlider
class ProductAdSliderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Fetch all ProductAdSlider instances
        product_ad_slider = ProductAdSlider.objects.all()
        serializer = ProductAdSliderSerializer(product_ad_slider, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
from .serializers import ItemSerializer
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Item
from .serializers import ItemSerializer
from rest_framework.permissions import AllowAny

class ItemSearchAPIView(APIView):
    permission_classes = [AllowAny]  # You can change this to IsAuthenticated if needed

    def get(self, request, *args, **kwargs):
        search_query = request.GET.get('search', '')  # Get the search query from the URL
        
        if len(search_query) < 2:
            return Response({"detail": "Search query must be at least 2 characters."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter items by name using the 'icontains' filter (case-insensitive)
        items = Item.objects.filter(name__icontains=search_query)[:2]  # Limit to 2 results

        # If no items are found, return an empty list
        if not items:
            return Response([], status=status.HTTP_200_OK)
        
        # Serialize the items
        serializer = ItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
