# 🐍 Python Virtual Environment Setup Guide

## ✅ Virtual Environment Created

A Python virtual environment has been created in:
```
c:\Users\DELL USER\Desktop\Zunto\server\venv\
```

---

## 🚀 How to Use the Virtual Environment

### **Activate the Virtual Environment**

**PowerShell (Recommended):**
```powershell
cd c:\Users\DELL USER\Desktop\Zunto\server
.\venv\Scripts\Activate.ps1
```

**Command Prompt (cmd):**
```cmd
cd c:\Users\DELL USER\Desktop\Zunto\server
venv\Scripts\activate.bat
```

**Git Bash:**
```bash
cd c:\Users\DELL USER\Desktop\Zunto\server
source venv/Scripts/activate
```

### **After Activation**
Your prompt should show `(venv)` prefix:
```
(venv) PS C:\Users\DELL USER\Desktop\Zunto\server>
```

---

## 📦 Install Dependencies in Virtual Environment

Once activated, install all required packages:

```powershell
# Make sure venv is activated (you should see (venv) in prompt)
pip install -r requirements.txt
```

---

## ⚠️ Important: Stop Current Backend First

Before using the virtual environment, **stop the currently running backend**:

1. Go to the terminal running `python manage.py runserver`
2. Press `Ctrl+C` to stop it
3. Then activate venv and restart with it

---

## ✅ Complete Setup Workflow

### **Terminal 1: Backend with Virtual Environment**
```powershell
# Navigate to server
cd c:\Users\DELL USER\Desktop\Zunto\server

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# You should see (venv) in prompt
# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the backend
python manage.py runserver 0.0.0.0:8000
```

### **Terminal 2: Frontend**
```powershell
# Navigate to client
cd c:\Users\DELL USER\Desktop\Zunto\client

# Start frontend dev server
npm run dev
```

---

## 🔍 Verify Virtual Environment is Active

When activated, check Python location:
```powershell
(venv) PS> python -c "import sys; print(sys.prefix)"
# Should output: C:\Users\DELL USER\Desktop\Zunto\server\venv
```

---

## 🗑️ Deactivate Virtual Environment

When done developing:
```powershell
(venv) PS> deactivate

# Prompt should no longer show (venv)
PS C:\Users\DELL USER\Desktop\Zunto\server>
```

---

## 📋 Why Virtual Environment?

✅ **Isolates** project dependencies  
✅ **Prevents** conflicts with system Python  
✅ **Ensures** reproducible environments  
✅ **Professional** development practice  
✅ **Required** for production deployment  

---

## 🚨 Common Issues

### **PowerShell execution policy error?**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **venv Scripts not found?**
Make sure you're in the correct directory:
```powershell
cd c:\Users\DELL USER\Desktop\Zunto\server
```

### **Still seeing packages from old Python?**
Deactivate and reactivate:
```powershell
deactivate
.\venv\Scripts\Activate.ps1
```

---

## 📚 What's in the venv?

```
venv/
├── Scripts/              # Python executables & activate scripts
│   ├── Activate.ps1      # PowerShell activation script
│   ├── activate.bat      # CMD activation script
│   ├── python.exe        # Python interpreter (venv)
│   └── pip.exe           # Package manager (venv)
├── Lib/                  # Installed packages
├── Include/              # C headers
└── pyvenv.cfg            # Virtual env config
```

---

## ✨ Best Practices

1. **Always activate venv before working** on the backend
2. **Add venv to .gitignore** (already done in most projects)
3. **Install new packages with venv active**: `pip install package-name`
4. **Update requirements.txt**: `pip freeze > requirements.txt`
5. **Share requirements.txt**, not venv folder

---

## 🎯 Next Steps

1. **Activate venv**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install all dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Restart the backend** (from Terminal 1):
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```

4. **Access your app**:
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000

---

**Status**: ✅ Virtual environment created and ready to use!
