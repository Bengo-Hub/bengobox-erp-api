from rest_framework import viewsets, status
from django.db.models import Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Contact
from hrm.employees.models import Employee
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions
from django.db.models import Q, Count, Sum
from django.db.models.functions import Trunc
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
from .serializers import *
from ecommerce.product.models import *
from core_orders.models import BaseOrder
from ecommerce.pos.models import Sales,salesItems
from ecommerce.product.serializers import ProductsSerializer
from authmanagement.serializers import UserSerializer
from ecommerce.stockinventory.models import StockInventory
from business.models import Bussiness, Branch, PickupStations
from addresses.models import AddressBook, DeliveryRegion

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Contact,ContactAccount,CustomerGroup
from .serializers import ContactSerializer,CustomerGroupSerializer
from django.http import Http404, JsonResponse
from django.db.models import Q
from .functions import generate_contact_id
from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Case, Value, When
from django.contrib.auth.hashers import make_password

class ContactsViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.annotate(
            is_walkin=Case(
                When(user__username__icontains='walkin', then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField(),
            )
        ).filter(is_deleted=False).order_by('-is_walkin').prefetch_related('accounts').select_related('user','customer_group', 'created_by')
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated,]
    pagination_class = LimitOffsetPagination  # Use the custom pagination class

    def get_object(self, pk):
        try:
            return Contact.objects.get(pk=pk)
        except Contact.DoesNotExist:
            raise Http404

    def get_queryset(self):
        queryset = super().get_queryset()
        query=self.request.query_params.get('query',None)
        contact_type=self.request.query_params.get('contact_type',None)
        account_type=self.request.query_params.get('account_type',None)
        branch_id = self.request.query_params.get('branch_id',None)
        #check if user user is linked to busness organisation or is a business owner
        user_org=None
        owner=None
        if hasattr(self.request.user,'employee') and hasattr(self.request.user.employee,'organisation'):
            user_org=self.request.user.employee.organisation
            queryset=queryset.filter(branch__business=user_org)
        if hasattr(self.request.user,'owner'):
            owner=self.request.user.owner
            queryset=queryset.filter(branch__business__owner=owner)
        if branch_id is not None:
            queryset = queryset.filter(branch__branch_id=branch_id)
        if query:
            queryset=queryset.filter(Q(user__username__icontains=query)|Q(user__first_name__icontains=query)|Q(user__first_name__icontains=query))
        if contact_type:
           queryset = queryset.filter(Q(contact_type=contact_type)) 
        if account_type:
           queryset = queryset.filter(Q(account_type=account_type))    
        return queryset 

    def create(self, request, *args, **kwargs):
        try:
            query_params=request.POST
            contact_type = query_params.get('contact_type','Individual')
            account_type=query_params.get('account_type','Customers')
            branch_id = self.request.query_params.get('branch_id',None)
            branch=Branch.objects.filter(Q(id=branch_id)|Q(business__owner=request.user)).first()
            if hasattr(request.user,'employee'):
                branch=Branch.objects.filter(business=request.user.employee.organisation)
            address =query_params.get('address',None)
            designation=query_params.get('designation','Mr')
            customer_group=query_params.get('customer_group',None)
            tax_number=query_params.get('tax_number',None)
            business=query_params.get('business',None)
            alternative_contact=query_params.get('alternative_contact',None)
            landline=query_params.get('landline',None)
            phone=query_params.get('phone','+254743793901')
            credit_limit=query_params.get('credit_limit',None)
            contact_id=query_params.get('contact_id',None)
            first_name = query_params.get('first_name','')
            last_name = query_params.get('last_name','')
            email = query_params.get('email',None)
            _contact_id=contact_id
            first_name=first_name if 'Customers' in account_type else str(business).split(' ')[0]
            username=str(first_name).lower().strip().replace(" ", "_") if 'Customers' in account_type else str(business).split(' ')[0].lower(),
            if contact_id==None or contact_id=='':
                _contact_id=generate_contact_id("C")
            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                "first_name":first_name if 'Customers' in account_type else str(business).split(' ')[0].lower(),
                "phone":phone,
                "last_name":last_name,
                "email":email if email else f'{str(first_name)}.{last_name}@gmail.com',
                "password":make_password("@User123"),
                "is_active":True
                }
            )
            Token.objects.update_or_create(user=user)
            biz=None
            if business is not None:
               biz,created=Bussiness.objects.update_or_create(owner=user,name=business)
            contact_defaults={
                "contact_id":_contact_id,
                "customer_group":CustomerGroup.objects.filter(id=customer_group).first(),
                "business":biz,
                "branch":branch,
                "designation":designation,
                "tax_number":tax_number,
                "credit_limit":credit_limit,
                "alternative_contact":alternative_contact,
                "landline":landline,
                }
            contact,created=Contact.objects.update_or_create(
                user=user,
                contact_type=contact_type,
                account_type=account_type,
                defaults=contact_defaults,
                )
            _,created=ContactAccount.objects.update_or_create(contact=Contact.objects.get(user=user))
            if address !=None:
                pickup_station=PickupStations.objects.filter(id=address).first()
                if pickup_station !=None:
                   adr,created=AddressBook.objects.update_or_create(user=user,address_label=pickup_station.pickup_location,phone=user.phone,other_phone=alternative_contact,address=pickup_station)
            return Response({'message':'Contact Created Successfully!'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error':f"Error:f{str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            query_params = request.POST
            contact = self.get_object(pk)
            # Update contact details based on query parameters
            contact_type = query_params.get('contact_type', contact.contact_type)
            address = query_params.get('address', None)
            designation = query_params.get('designation', contact.designation)
            customer_group = query_params.get('customer_group', contact.customer_group)
            account_type = query_params.get('account_type', contact.account_type)
            tax_number = query_params.get('tax_number', contact.tax_number)
            business = query_params.get('business', contact.business)
            alternative_contact = query_params.get('alternative_contact', contact.alternative_contact)
            landline = query_params.get('landline', contact.landline)
            credit_limit = query_params.get('credit_limit', contact.credit_limit)
            contact_id = query_params.get('contact_id', contact.contact_id)
            first_name = query_params.get('first_name', contact.user.first_name)
            last_name = query_params.get('last_name', contact.user.last_name)
            email = query_params.get('email', contact.user.email)

            # Update user details if necessary
            contact.user.username = str(first_name).lower().strip().replace(" ", "_")
            contact.user.first_name = first_name
            contact.user.last_name = last_name
            contact.user.email = email if email else f'{str(first_name)}.{last_name}@gmail.com'
            contact.user.save()

            # Update or create related objects
            biz = None
            if business is not None:
                biz, created = Bussiness.objects.get_or_create(owner=contact.user, name=business)

            contact_defaults = {
                "contact_type": contact_type,
                "account_type": account_type,
                "customer_group": CustomerGroup.objects.filter(id=customer_group).first(),
                "business": biz,
                "designation": designation,
                "tax_number": tax_number,
                "credit_limit": credit_limit,
                "alternative_contact": alternative_contact,
                "landline": landline,
            }
            contact.contact_type = contact_type
            contact.contact_id = contact_id
            for key, value in contact_defaults.items():
                setattr(contact, key, value)
            contact.save()

            # Update or create related objects
            ContactAccount.objects.update_or_create(contact=contact)

            # Update address if provided
            if address is not None:
                pickup_station = PickupStations.objects.filter(id=address).first()
                if pickup_station is not None:
                    adr, created = AddressBook.objects.get_or_create(
                        user=contact.user,
                        address_label=pickup_station.pickup_location,
                        phone=contact.user.phone,
                        other_phone=alternative_contact,
                        address=pickup_station
                    )

            return Response({'message': 'Contact Updated Successfully!'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f"Error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        instance = self.get_object(pk=pk)
        instance.is_deleted=True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CustomerGroupViewSet(viewsets.ModelViewSet):
    queryset = CustomerGroup.objects.all()
    serializer_class = CustomerGroupSerializer
    permission_classes = [permissions.IsAuthenticated,]

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated,])
def top_buyers(request):
    branch_id = request.GET.get('branch_id', None)
    branch=Branch.objects.filter(Q(id=branch_id)|Q(is_main_branch=True)).first()
    if branch == None:
       biz=Bussiness.objects.filter(user=request.user).first() if request.user.businesses else request.user.employee.orgisation 
    if request.user.is_superuser:
        top_customers = BaseOrder.objects.annotate(
            total_spent=Sum('order_amount')).values('customer__user__pic', 'payment_status', 'customer__addresses__region', 'customer__user__first_name', 'customer__user__last_name', 'total_spent').filter(total_spent__gte=50).order_by('-total_spent').distinct()[:5]
    elif branch != None:
        top_customers = Sales.objects.filter(saleitems__product__stock_item__branch__business=biz).annotate(
            total_spent=Sum('order_amount')).values('customer__user__pic','payment_status','customer__addresses__region', 'customer__user__first_name', 'customer__user__last_name', 'total_spent').filter(total_spent__gte=50).order_by('-total_spent').distinct()[:5]
    else:
        top_customers = ""
    return Response(list(top_customers))

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated,])
def top_products(request):
    branch_id=request.GET.get('branch_id',None)
    branch = Branch.objects.filter(id=branch_id).first()
    employee = Employee.objects.filter(user=request.user).first()
    if request.user.is_superuser:
        top_products = StockInventory.objects.annotate(total_sales=Sum('salesitems__qty')).filter(total_sales__gte=1).values(
            "product__sku","product__images__image", "product__title","product__stock__variation__title", "product__stock__variation__sku","total_sales","product__stock__id").order_by('total_sales')[:5]
    elif hasattr(request.user,'owner'):
        biz=Bussiness.objects.filter(business=biz).first()
        branch=biz.branches.filter(is_main_branch=True).first()
        top_products = StockInventory.objects.filter(branch=branch).annotate(total_sales=Sum('salesitems__qty')).filter(total_sales__gte=1).values(
            "product__sku", "product__title","product__stock__variation__title", "product__stock__variation__sku", "total_sales").distinct().order_by('total_sales')[:5]
    elif hasattr(request.user,'employee'):
        biz=request.user.employee.organisation
        branch=biz.branches.filter(is_main_branch=True).first()
        top_products = StockInventory.objects.filter(branch=branch).annotate(total_sales=Sum('salesitems__qty')).filter(total_sales__gte=1).values(
            "product__sku","product__product_images", "product__title","product__stock__variation__title", "product__stock__variation__sku", "total_sales").distinct().order_by('total_sales')[:5]
    else:
        top_products = []
    return Response(list(top_products))

class SaleAnalyticsViewSet(viewsets.ViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductsSerializer

    def list(self, request):
        print(request.user)
        sales_queryset=Sales.objects.filter(status='paid')
        # get vendor or vendor user
        employee = Employee.objects.filter(user=request.user).first()
        # Get the selected filters
        filter = request.query_params.get('filter', 'Monthly')
        now = datetime.now()
        date = request.query_params.get('date', now.strftime('%Y-%m-%d'))
        # Determine the time interval for the selected filter
        if filter == 'Weekly':
            interval = 'day'
            start_date = datetime.strptime(date, '%Y-%m-%d').date() - timedelta(days=7)
        elif filter == 'Monthly':
            interval = 'week'
            start_date = datetime.strptime(date, '%Y-%m-%d').date().replace(day=1) - timedelta(days=1)
        elif filter == 'Yearly':
            interval = 'month'
            start_date = datetime.strptime(date, '%Y-%m-%d').date().replace(month=1, day=1) - timedelta(days=1)
         # Query the database to get the total sales for the selected period
        total_sales_current_period = sales_queryset.filter(date_added__gte=start_date, date_added__lte=date).aggregate(total__sum=Sum('grand_total'))['total__sum'] or 0
        # Query the database to get the total sales for the previous period
        total_sales_previous_period = sales_queryset.filter(date_added__gte=start_date - timedelta(days=1), date_added__lte=datetime.strptime(
            date, '%Y-%m-%d').date() - timedelta(days=1)).aggregate(total__sum=Sum('grand_total'))['total__sum'] or 0
        # print(total_sales_current_period)
        # print(total_sales_previous_period)

        # Calculate the sales growth rate
        sales_growth_rate=0
        if total_sales_previous_period == 0:
            if total_sales_current_period >0:
                sales_growth_rate = 100
        else:
            sales_diff = total_sales_current_period - total_sales_previous_period
            sales_growth_rate = round(
                (sales_diff / total_sales_previous_period) * 100, 2)

        # Query the database for the top 3 selling categories based on the selected filter
        top_categories = salesItems.objects.annotate(date=Trunc('sale__date_added', interval)).values('stock_item__product__category__name', 'date').annotate(
            total=Sum('unit_price')).values('stock_item__product__category__name', 'sale__grand_total').order_by('-sale__grand_total')
        if employee != None:
            top_categories = top_categories.filter(
                stock_item__location__business=employee.organisation)[:3]
        else:
            top_categories = top_categories[:3]
        # Format the data into the desired format
        orders = BaseOrder.objects.annotate(date=Trunc(
            'created_at', interval)).values('order_id').annotate(order_count=Count('order_id')).order_by('created_at')
        customers = Contact.objects.annotate(date=Trunc(
            'user__date_joined', interval)).values("user__id").annotate(customer_coount=Count('user__id')).order_by('user__date_joined')
        data = []
        order_series = []
        customer_series = []
        customer_count = Contact.objects.count()
        order_count = BaseOrder.objects.count()
        sales_count = salesItems.objects.count()
        conversion_ratio=0.00
        if customer_count > 0 and sales_count >0:
           conversion_ratio = sales_count/customer_count
        total_sales_amount = sales_queryset.aggregate(
            total=Sum('grand_total'))['total']
        for c in customers:
            customer_series.append(c['customer_coount'])
        for od in orders:
            order_series.append(od['order_count'])
        for category in top_categories:
            name = category['stock_item__product__category__name']
            sales_data = salesItems.objects.annotate(date=Trunc('sale__date_added', interval)).values(
                'date').annotate(total=Sum('unit_price')).filter(stock_item__product__category__name=name).order_by('date')
            # Create a list of total sales for each interval
            sales_list = []
            for sales in sales_data:
                sales_list.append(sales['total'])
            # Add the category and sales data to the result list
            for item in data:
                if item['name'] == name:
                    break
            else:
                data.append({'name': name, 'data': sales_list})
        data.append({"sales_amount": total_sales_amount,
                    "sales_count": sales_count, "conversion_ratio": conversion_ratio, "orders": order_count, "customers": customer_count, "order_series": order_series, "customer_series": customer_series, "growth_rate": sales_growth_rate})
        return Response(list(data), status=status.HTTP_200_OK)
