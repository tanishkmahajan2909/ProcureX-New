-- Replace 1 at the bottom with the RFQ you want to evaluate.
WITH latest_rating AS (
  SELECT
    vendor_id,
    rating_score,
    ROW_NUMBER() OVER (
      PARTITION BY vendor_id
      ORDER BY rating_date DESC, rating_id DESC
    ) AS rn
  FROM vendor_rating
),
quote_data AS (
  SELECT
    q.quotation_id,
    q.rfq_id,
    v.vendor_id,
    v.vendor_name,
    q.quoted_price,
    q.delivery_days,
    COALESCE(lr.rating_score, 0) AS rating_score
  FROM quotation q
  JOIN vendor v ON v.vendor_id = q.vendor_id
  LEFT JOIN latest_rating lr
    ON lr.vendor_id = v.vendor_id AND lr.rn = 1
  WHERE q.rfq_id = 1
),
normalized AS (
  SELECT
    *,
    1 - (quoted_price - MIN(quoted_price) OVER ()) /
      NULLIF(MAX(quoted_price) OVER () - MIN(quoted_price) OVER (), 0) AS price_score,
    1 - (delivery_days - MIN(delivery_days) OVER ()) /
      NULLIF(MAX(delivery_days) OVER () - MIN(delivery_days) OVER (), 0) AS delivery_score,
    rating_score / 5.0 AS rating_norm
  FROM quote_data
)
SELECT
  vendor_name,
  quoted_price,
  delivery_days,
  rating_score,
  ROUND(
    (0.5 * COALESCE(price_score, 1)) +
    (0.2 * COALESCE(delivery_score, 1)) +
    (0.3 * rating_norm),
    3
  ) AS final_score
FROM normalized
ORDER BY final_score DESC;
