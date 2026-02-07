# Zunto Backend & Frontend Setup Script (Windows)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Zunto - Backend & Frontend Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if running from correct directory
if (-not (Test-Path "manage.py")) {
    Write-Host "❌ Error: Please run this script from the Zunto root directory" -ForegroundColor Red
    exit 1
}

# Backend Setup
Write-Host "📦 Setting up Backend..." -ForegroundColor Yellow
Write-Host ""

Write-Host "1️⃣  Installing Python dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host ""
Write-Host "2️⃣  Running migrations..." -ForegroundColor Cyan
python manage.py migrate

Write-Host ""
Write-Host "3️⃣  Creating superuser (optional)..." -ForegroundColor Cyan
$createSuperuser = Read-Host "Create superuser? (y/n)"
if ($createSuperuser -eq "y") {
    python manage.py createsuperuser
}

Write-Host ""
Write-Host "✅ Backend setup complete!" -ForegroundColor Green
Write-Host ""

# Frontend Setup
Write-Host "⚛️  Setting up Frontend..." -ForegroundColor Yellow
Write-Host ""

Push-Location client

Write-Host "1️⃣  Installing Node dependencies..." -ForegroundColor Cyan
npm install

Write-Host ""
Write-Host "2️⃣  Creating .env.local file..." -ForegroundColor Cyan
if (-not (Test-Path ".env.local")) {
    $envContent = @"
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Zunto
VITE_APP_VERSION=1.0.0
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_CHAT=true
VITE_ENABLE_NOTIFICATIONS=true
"@
    Set-Content -Path ".env.local" -Value $envContent
    Write-Host "✅ .env.local created" -ForegroundColor Green
} else {
    Write-Host "ℹ️  .env.local already exists" -ForegroundColor Gray
}

Pop-Location

Write-Host ""
Write-Host "✅ Frontend setup complete!" -ForegroundColor Green
Write-Host ""

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Setup Complete! 🎉" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1️⃣  Start Backend (from Zunto root directory):" -ForegroundColor Cyan
Write-Host "   python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "2️⃣  Start Frontend (from client directory):" -ForegroundColor Cyan
Write-Host "   npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "3️⃣  Open browser:" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5173 (or http://localhost:5174)" -ForegroundColor White
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   Admin:    http://localhost:8000/admin" -ForegroundColor White
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Yellow
Write-Host "   - Backend must be running before frontend" -ForegroundColor Gray
Write-Host "   - Make sure ports 8000, 5173, 5174 are available" -ForegroundColor Gray
Write-Host "   - Check CORS settings if API calls fail" -ForegroundColor Gray
Write-Host ""
