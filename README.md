# BOQ Manager

**A comprehensive FastAPI + React application for managing telecommunications infrastructure projects, bills of quantities, and resource optimization.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.0-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.1.0-blue.svg)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue.svg)](https://postgresql.org)

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Description

BOQ Manager is a full-stack web application designed for telecommunications infrastructure project management. It provides comprehensive tools for managing Bills of Quantities (BOQ), Radio Access Network (RAN) projects, and Latest Estimate/Resource Optimization Planning (LE/ROP).

### What problems does it solve?

- **Project Cost Management**: Track and manage telecommunications infrastructure project costs and materials
- **Inventory Management**: Monitor equipment and material inventory across multiple project types
- **Resource Optimization**: Plan and optimize resource allocation for project efficiency
- **Multi-Level Planning**: Support hierarchical project structures with detailed specifications
- **Data Integration**: Handle various data formats and provide seamless data import/export capabilities

## Features

- 🔐 **Authentication & Authorization**: JWT-based authentication with role-based access control
- 📊 **Multi-Domain Project Management**:
  - BOQ (Bill of Quantities) projects
  - RAN (Radio Access Network) projects
  - LE/ROP (Latest Estimate/Resource Optimization Planning) projects
- 📦 **Inventory Management**: Track materials and equipment across projects
- 📋 **Hierarchical Project Structure**: Multi-level project organization (Levels 1-3)
- 📄 **Document Management**: Support for LLD (Low Level Design) specifications
- 📈 **Resource Planning**: Monthly distribution and package management
- 🔄 **Data Import/Export**: Excel/CSV support for bulk operations
- 🎯 **RAG-Powered Analytics**: AI-driven project insights and recommendations
- 📱 **Responsive UI**: Modern React-based frontend with intuitive navigation

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** - SQL toolkit and Object-Relational Mapping
- **PostgreSQL** - Primary database
- **Alembic** - Database migration tool
- **JWT** - Authentication and authorization
- **Bcrypt** - Password hashing
- **Uvicorn** - ASGI server

### Frontend
- **React 19.1** - User interface library
- **Vite** - Build tool and development server
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls
- **React Select** - Enhanced select components
- **React DatePicker** - Date selection components
- **React Icons** - Icon library

### AI/ML Components
- **Transformers** - Natural language processing
- **Sentence Transformers** - Text embeddings
- **FAISS** - Vector similarity search
- **PyTorch** - Machine learning framework

### Development Tools
- **ESLint** - JavaScript/React linting
- **Pre-commit** - Code quality hooks
- **OpenAPI Generator** - API client generation

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 12+
- Git

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd BOQ
   ```

2. **Set up Python virtual environment:**
   ```bash
   cd be
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database and security settings
   ```

5. **Set up database:**
   ```bash
   alembic upgrade head
   python SeedAdmin.py
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd ../fe
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment:**
   ```bash
   # Edit .env.development and .env.production as needed
   ```

## Usage

### Development Mode

1. **Start the backend server:**
   ```bash
   cd be
   python main.py
   # Server runs on http://localhost:8003
   ```

2. **Start the frontend development server:**
   ```bash
   cd fe
   npm run dev
   # Frontend runs on http://localhost:5173
   ```

### Production Mode

1. **Build the frontend:**
   ```bash
   cd fe
   npm run build
   ```

2. **Start the backend server:**
   ```bash
   cd be
   python main.py
   ```

### API Endpoints

The application provides RESTful APIs for:

- **Authentication**: `/auth/login`, `/auth/register`
- **BOQ Projects**: `/boq/projects`, `/boq/inventory`, `/boq/levels`
- **RAN Projects**: `/ran/projects`, `/ran/inventory`, `/ran/lvl3`
- **LE/ROP Projects**: `/le/projects`, `/le/packages`, `/le/distribution`
- **Admin**: `/admin/users`, `/admin/roles`

## Configuration

### Environment Variables

Create a `.env` file in the `be/` directory:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/boq_db

# JWT Authentication
SECRET_KEY=your_super_secret_jwt_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Admin Setup
ADMIN_PASSWORD=your_admin_password_here

# Optional: AI/RAG Configuration
HF_TOKEN=your_huggingface_token
MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

### Database Setup

The application uses PostgreSQL. Ensure your database is created and accessible:

```sql
CREATE DATABASE boq_db;
CREATE USER boq_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE boq_db TO boq_user;
```

## API Documentation

Once the backend is running, comprehensive API documentation is available at:

- **Swagger UI**: [http://localhost:8003/docs](http://localhost:8003/docs)
- **ReDoc**: [http://localhost:8003/redoc](http://localhost:8003/redoc)

The API follows RESTful conventions and includes:
- Request/response schemas
- Authentication requirements
- Example requests and responses
- Error handling documentation

## Project Structure

```
BOQ/
├── be/                          # Backend (FastAPI)
│   ├── main.py                 # Application entry point
│   ├── SeedAdmin.py           # Admin user setup
│   ├── Database/              # Database configuration
│   ├── APIs/                  # API route handlers
│   │   ├── Core.py           # Authentication utilities
│   │   ├── Admin/            # Admin management
│   │   ├── BOQ/              # BOQ project routes
│   │   ├── RAN/              # RAN project routes
│   │   └── LE/               # LE/ROP project routes
│   ├── Models/               # SQLAlchemy models
│   ├── Schemas/              # Pydantic schemas
│   ├── RAG/                  # AI/RAG components
│   └── alembic/              # Database migrations
├── fe/                         # Frontend (React)
│   ├── src/
│   │   ├── components/       # Reusable components
│   │   ├── RanComponents/    # RAN-specific components
│   │   ├── api/              # API client code
│   │   └── utils/            # Utility functions
│   ├── public/               # Static assets
│   └── package.json          # Node.js dependencies
└── README.md                   # This file
```

## Testing

### Backend Tests

```bash
cd be
python -m pytest tests/
```

### Frontend Tests

```bash
cd fe
npm run test
```

### Linting

```bash
# Backend
cd be
flake8 .

# Frontend
cd fe
npm run lint
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes and commit:**
   ```bash
   git commit -am 'Add some feature'
   ```
4. **Push to the branch:**
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Submit a pull request**

### Code Style Guidelines

- **Python**: Follow PEP 8, use type hints
- **JavaScript/React**: Follow ESLint configuration
- **Commits**: Use conventional commit messages
- **Documentation**: Update relevant documentation for new features

## Roadmap

- [ ] **Enhanced Reporting**: Advanced analytics and custom report generation
- [ ] **Mobile Application**: React Native mobile app for field operations
- [ ] **Real-time Collaboration**: WebSocket-based real-time project updates
- [ ] **Advanced AI Features**: Predictive analytics for project planning
- [ ] **Integration APIs**: Third-party system integrations (ERP, CRM)
- [ ] **Audit Trail**: Comprehensive change tracking and audit logs

## FAQ / Troubleshooting

### Common Issues

**Q: Database connection fails**
A: Ensure PostgreSQL is running and credentials in `.env` are correct.

**Q: Frontend can't reach backend API**
A: Check that backend is running on port 8003 and CORS is properly configured.

**Q: Authentication tokens expire quickly**
A: Adjust `ACCESS_TOKEN_EXPIRE_MINUTES` in your `.env` file.

**Q: AI/RAG features not working**
A: Ensure you have a valid Hugging Face token and required ML dependencies are installed.

### Performance Tips

- Use database indexes for frequently queried fields
- Implement pagination for large data sets
- Cache static data using Redis (optional enhancement)
- Optimize frontend bundle size with code splitting

## License

This project is proprietary software. All rights reserved.

## Acknowledgements

- **FastAPI** - For the excellent web framework
- **React Team** - For the powerful UI library
- **SQLAlchemy** - For robust ORM capabilities
- **Hugging Face** - For AI/ML model infrastructure
- **Contributors** - Thanks to all team members who have contributed to this project

---

**Note**: This is an active project under continuous development. Features and documentation are regularly updated. For the latest information, please refer to the project repository and API documentation.