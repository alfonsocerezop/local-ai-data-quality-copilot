select
    cast(source_row_number as bigint) as source_row_number,
    source_dataset,
    source_file,

    cast(order_id as bigint) as order_id,
    cast(customer_id as bigint) as customer_id,
    cast(order_date as date) as order_date,
    cast(order_amount as decimal(12, 2)) as order_amount,
    lower(trim(order_status)) as order_status

from {{ source('raw', 'raw_orders') }}