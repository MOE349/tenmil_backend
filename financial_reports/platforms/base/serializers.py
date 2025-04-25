from configurations.base_features.serializers.base_serializer import BaseSerializer
from financial_reports.models import *
import numpy_financial as npf


class CapitalCostBaseSerializer(BaseSerializer):
    class Meta:
        model = CapitalCost
        fields = '__all__'

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
        maintnance_cost_per_hr = 48
        operational_cost_per_hr = operational_cost_per_year / expected_hours
        total_cost_per_hr = operational_cost_per_hr + maintnance_cost_per_hr + capital_cost_per_hr
        response['table'] = {
            "Hi Severity Exp Hours":expected_hours,
            "Purchase Cost": f"{purchase_cost}$",
            "Resale Cost Low Sev": f"{instance.resale_cost}$",
            "FINANCE YEARS": finance_years,
            "Monthly payment":f"{round(monthly_payment, 2)}$",
            "Interest amount":f"{ round(interst_amount, 2)}$",
            "Interest rate": f"{interest_rate}%",
            "Captial Work Cost": capital_work_cost,
            "Operational Cost/ Year": f"{operational_cost_per_year}$",
            "Yearly Hours": yearly_hours,
            "Capital Cost/Hr": f"{round(capital_cost_per_hr, 2)}$",
            "Maintenance Cost/Hr": f"{maintnance_cost_per_hr}$",
            "Operational Cost/Hr":f"{ round(operational_cost_per_hr, 2)}$",
            "Total Cost/Hr": f"{round(total_cost_per_hr, 2)}$"
        }

        return response


