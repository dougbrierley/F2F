# API Specification

## Order

- Order date format: DD/MM/YYYY
- Prices are in pence (integer)

```Typescript
{
  id: string | null,
  orderNumber: string,
  orderDate: string,
  customer: {
    id: string | null,
    name: string,
    address1: string,
    address2: string | null,
    postcode: string,
    city: string,
    country: string,
  },
  growers: [
    {
      id: string | null,
      name: string,
      lines: [
        {
          id: string | null,
          quantity: number,
          product: {
            id: string | null,
            name: string,
            description: string | null,
            price: number,
            unit: string
          },
        }
      ]
    }
  ]
}
```
