#!/bin/bash

echo "======================================"
echo "  Zunto - Backend & Frontend Setup"
echo "======================================"
echo ""

# Check if running from correct directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the Zunto root directory"
    exit 1
fi

# Backend Setup
echo "📦 Setting up Backend..."
echo ""

echo "1️⃣  Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "2️⃣  Running migrations..."
python manage.py migrate

echo ""
echo "3️⃣  Creating superuser (optional)..."
read -p "Create superuser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

echo ""
echo "✅ Backend setup complete!"
echo ""

# Frontend Setup
echo "⚛️  Setting up Frontend..."
echo ""

cd client || exit 1

echo "1️⃣  Installing Node dependencies..."
npm install

echo ""
echo "2️⃣  Creating .env.local file..."
if [ ! -f ".env.local" ]; then
    cat > .env.local << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Zunto
VITE_APP_VERSION=1.0.0
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_CHAT=true
VITE_ENABLE_NOTIFICATIONS=true
EOF
    echo "✅ .env.local created"
else
    echo "ℹ️  .env.local already exists"
fi

echo ""
echo "✅ Frontend setup complete!"
echo ""

echo "======================================"
echo "  Setup Complete! 🎉"
echo "======================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1️⃣  Start Backend (from Zunto root directory):"
echo "   python manage.py runserver"
echo ""
echo "2️⃣  Start Frontend (from client directory):"
echo "   npm run dev"
echo ""
echo "3️⃣  Open browser:"
echo "   Frontend: http://localhost:5173 (or http://localhost:5174)"
echo "   Backend:  http://localhost:8000"
echo "   Admin:    http://localhost:8000/admin"
echo ""
echo "💡 Tips:"
echo "   - Backend must be running before frontend"
echo "   - Make sure ports 8000, 5173, 5174 are available"
echo "   - Check CORS settings if API calls fail"
echo ""
