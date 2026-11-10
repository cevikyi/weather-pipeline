select
	location_id,
	weather_date,
	count(*)

from {{ref('daily_weather')}}
group by 1,2
having count(*) > 1
