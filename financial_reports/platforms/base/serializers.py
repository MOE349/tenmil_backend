from configurations.base_features.serializers.base_serializer import BaseSerializer
from financial_reports.models import *
import numpy_financial as npf


class CapitalCostBaseSerializer(BaseSerializer):
    class Meta:
        model = CapitalCost
        fields = '__all__'
    
    def calculate_maint_coast_per_hour(self):
        return 48

    def to_representation(self, instance):
        response = super().to_representation(instance)
        capital_work_cost = instance.capital_work_cost
        expected_hours = instance.expected_hours
        interest_rate = instance.interest_rate
        finance_years = instance.finance_years
        purchase_cost = instance.purchase_cost
        monthly_payment = npf.pmt((interest_rate/100)/12, finance_years*12,  (purchase_cost * -1))
        # monthly_payment = (((interest_rate/12) * (1 + (interest_rate/12))**(finance_years/12) ) * purchase_cost ) / ((1+ (interest_rate/12))**(finance_years/12) -1)
        interst_amount = (monthly_payment * 60) - purchase_cost
        yearly_hours = expected_hours / finance_years
        capital_cost_per_hr = ((purchase_cost + interst_amount + capital_work_cost) - instance.resale_cost) / expected_hours
        operational_cost_per_year = instance.operational_cost_per_year
        maintnance_cost_per_hr = self.calculate_maint_coast_per_hour()
        operational_cost_per_hr = operational_cost_per_year / expected_hours
        total_cost_per_hr = operational_cost_per_hr + maintnance_cost_per_hr + capital_cost_per_hr
        response['table'] = {
            "expected_hours":expected_hours,
            "monthly_payment":f"{round(monthly_payment, 2)}$",
            "interst_amount":f"{ round(interst_amount, 2)}$",
            "operational_cost_per_year": f"{operational_cost_per_year}$",
            "yearly_hours": yearly_hours,
            "capital_cost_per_hr": f"{round(capital_cost_per_hr, 2)}$",
            "maintnance_cost_per_hr": f"{maintnance_cost_per_hr}$",
            "operational_cost_per_hr":f"{ round(operational_cost_per_hr, 2)}$",
            "total_cost_per_hr": f"{round(total_cost_per_hr, 2)}$"
        }

        return response


