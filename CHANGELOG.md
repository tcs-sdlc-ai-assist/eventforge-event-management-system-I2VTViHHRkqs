# Changelog

All notable changes to the EventForge project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-01

### Added

#### Authentication & User Management
- User registration with email validation and secure password hashing using bcrypt
- User login with JWT-based authentication and session management
- Protected routes with role-based access control (Admin, Organizer, Attendee)
- User profile viewing and editing
- Password change functionality for authenticated users

#### Event Management (CRUD)
- Full create, read, update, and delete operations for events
- Event creation with title, description, date/time, location, and capacity settings
- Support for multiple ticket types per event (free, paid, VIP)
- Ticket type configuration with name, price, quantity, and availability
- Event image upload support
- Event status management (draft, published, cancelled, completed)
- Event category assignment for organized browsing

#### RSVP & Registration System
- Attendee RSVP and ticket registration for published events
- Ticket type selection during registration
- Registration confirmation and tracking
- Capacity enforcement preventing over-registration
- Registration cancellation by attendees
- Organizer view of all registrations per event

#### Check-In System
- QR code or manual check-in for registered attendees
- Real-time check-in status tracking per event
- Check-in validation against registration records
- Organizer-facing check-in management interface
- Check-in statistics and attendance counts

#### Event Search & Browse
- Full-text search across event titles and descriptions
- Browse events by category
- Filter events by date range, location, and status
- Pagination for event listings
- Upcoming events display on the home page
- Event detail pages with full information and registration options

#### Organizer Dashboard
- Overview of all events created by the organizer
- Registration and attendance statistics per event
- Event performance metrics and summaries
- Quick actions for event management (edit, publish, cancel)
- Attendee list export and management

#### Admin Dashboard
- System-wide event and user statistics
- Category management with full CRUD operations (create, edit, delete categories)
- User management and role assignment
- Platform-wide event moderation capabilities
- System health and activity overview

#### User Interface
- Responsive design built with Jinja2 templates and Tailwind CSS
- Mobile-first layout adapting to all screen sizes
- Consistent navigation with role-aware sidebar and header
- Clean event cards with key information at a glance
- Form validation with user-friendly error messages
- Flash messages for action confirmations and error notifications
- Dark-mode-ready utility class structure

#### API & Architecture
- RESTful API built with FastAPI and Python 3.11+
- Async SQLAlchemy 2.0 with aiosqlite for database operations
- Pydantic v2 schemas for request/response validation
- Dependency injection for database sessions and authentication
- Structured logging throughout the application
- CORS middleware configuration for cross-origin support
- Lifespan-based startup and shutdown event handling