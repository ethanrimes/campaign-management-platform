# Using psql directly
```
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres" -f backend/db/migrations/000_xxxxx.sql
```

# Or if you have SUPABASE_DB_URL in your environment
```
psql $SUPABASE_DB_URL -f backend/db/migrations/000_xxxxx.sql
```