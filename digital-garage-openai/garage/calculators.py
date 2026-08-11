import math
def tire_diameter_in(width_mm,aspect_pct,wheel_in): return wheel_in+2*(width_mm*aspect_pct/100)/25.4
def tire_circumference_in(width_mm,aspect_pct,wheel_in): return math.pi*tire_diameter_in(width_mm,aspect_pct,wheel_in)
def speed_error_percent(stock,new): return (new/stock-1)*100
def rpm_at_speed(mph,tire_diameter_in_value,gear_ratio,final_drive): return mph*gear_ratio*final_drive*336/tire_diameter_in_value
def psi_to_kpa(v): return v*6.894757293
def f_to_c(v): return (v-32)*5/9
def cost_per_mile(total_cost,miles): return total_cost/miles if miles else None
