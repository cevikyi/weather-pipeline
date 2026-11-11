

select

	location_id,
	date(valid_time, 'Europe/Istanbul') as weather_date,
	min(temperature_2m) as temp_min,
	max(temperature_2m) as temp_max,
	round(avg(temperature_2m), 1) as temp_avg,
	count(*) as hour_count,                                -- bu gün kaç saatlik veriye dayanıyor
    count(*) = 24 as is_complete_day                       -- 24 saatin hepsi var mı? (true/false)

	from {{ref('stg_weather_hourly')}}
group by
		location_id,weather_date