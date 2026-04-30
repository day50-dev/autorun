# migrate

Run database migrations safely with backup and rollback option.

## Detect

- If file manage.py exists, set framework = django
- If file artisan exists, set framework = laravel
- If file prisma/schema.prisma exists, set framework = prisma
- Else ask "What's your database framework?" → store in framework

## Ask

- **backup**: "Create backup before migrating?"
  - Type: confirm
  - Default: yes
  - Store: .haby/migrate.json

- **dry_run**: "Show migration plan first?"
  - Type: confirm
  - Default: yes
  - Store: .haby/migrate.json

## Execute

1. If ${backup} == yes and ${framework} == django: "python manage.py dumpdata > backup-$(date +%Y%m%d).json"
2. If ${dry_run} == yes and ${framework} == django: "python manage.py migrate --plan"
3. If ${framework} == django: "python manage.py migrate"
4. If ${framework} == laravel: "php artisan migrate"
5. If ${framework} == prisma: "npx prisma migrate dev"

## Save

Save answers to .haby/migrate.json