select
    source_row_number,
    source_dataset,
    source_file,
    order_id,
    customer_id,
    order_date,
    order_amount,
    order_status

from {{ ref('stg_orders') }}