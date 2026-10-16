# ADR 0001: raw.weather_hourly append-only

- Status: Accepted
- Date: 2026-10-16

## Context
<!-- 3 tane önemli detay var
--1. Satır satır bir veri yok, paralel diziler var
--2. Timezone yok. Timestampe değiştirmek gerekecek
--3. Bugun gelecek yarın hava durumu "tahmin", yarın gelecek ise daha doğru. Bunlara bir append lazım

## Decision
<!-- Grain ne? Zaman hangi timezone/tipte saklanıyor? -->
-- Day, location_id, valid_time, ingested_at

## Consequences
<!-- Bu kararın bedeli ne, karşılığında ne kazanıyoruz? (staging, ML) -->
-- Biraz daha pahalı olacak

## Alternatives considered
<!-- Upsert/overwrite: neden reddedildi? -->
-- Model kurabilmek için append olmayan seyleri reddediyoruz
