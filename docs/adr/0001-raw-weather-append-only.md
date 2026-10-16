# ADR 0001: raw.weather_hourly append-only

- Status: Accepted
- Date: 2026-10-16

## Context

--1. Satır satır bir veri yok, paralel diziler var
--2. Timezone yok. Timestampe değiştirmek gerekecek. PI'yi varsayılan GMT ile çağırırsantimezone varsayılanı GMT. Open-Meteo docs zamanlar zaten UTC gelir. Raw'a TIMESTAMP (UTC) yaz, yerel güne çevirmeyi dbt'de yap.
--3. Bugun gelecek yarın hava durumu "tahmin", yarın gelecek ise daha doğru. Bunlara bir append lazım

## Decision

-- Day, location_id, valid_time, ingested_at

## Consequences

-- Biraz daha pahalı olacak

## Alternatives considered

-- Model kurabilmek için append olmayan seyleri reddediyoruz
