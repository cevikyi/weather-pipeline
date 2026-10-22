select

	location_id,
	valid_time,
	temperature_2m,
	ingested_at

from {{ source('raw', 'weather_hourly') }}
qualify row_number() over(
		partition by 	location_id,valid_time order by ingested_at desc
	) = 1