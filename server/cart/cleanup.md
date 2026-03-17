# Cart Cleanup System

## Overview
Automated and manual cleanup of old guest carts while preserving analytics data.

## Automated Cleanup (Celery)
- **Task**: `cleanup_old_guest_carts`
- **Schedule**: Weekly (Sunday 5 AM)
- **Default**: Deletes guest carts older than 30 days
- **Protected**: Carts with abandonment records are never deleted

## Manual Cleanup (Management Command)

### Check what would be deleted
```bash
python manage.py cleanup_old_carts --dry-run
```

### Delete old guest carts (30 days default)
```bash
python manage.py cleanup_old_carts
```

### Delete carts older than 60 days
```bash
python manage.py cleanup_old_carts --days=60
```

### View cleanup statistics
```bash
python manage.py test_cleanup
python manage.py test_cleanup --days=60
```

## Safety Features
- ✅ Never deletes carts with abandonment records (analytics preserved)
- ✅ Only deletes guest carts (user carts are protected)
- ✅ Dry-run mode available
- ✅ Detailed logging
- ✅ Idempotent (safe to run multiple times)

## Scheduled Tasks Summary
1. **2 AM** - Detect abandoned carts
2. **3 AM** - Send abandonment reminders
3. **4 AM** - Calculate user scores
4. **5 AM Sunday** - Cleanup old guest carts