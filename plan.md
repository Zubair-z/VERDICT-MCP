# Project Plan

## TASK_001: Setup authentication module
- [ ] Create auth_handler.py with login/logout functions
- [ ] Add JWT token validation helpers
- [ ] Write error handling for invalid credentials
- Depends on:
- Status: PENDING

## TASK_002: Build dashboard UI
- [ ] Create main_window.py with PySide6 glassmorphic design
- [ ] Implement sidebar navigation with neon accents
- [ ] Add dark theme stylesheet
- Depends on: TASK_001
- Status: PENDING

## TASK_003: Integrate database layer
- [ ] Create db_handler.py with connection pooling
- [ ] Add CRUD operations for user data
- [ ] Write comprehensive exception handling
- Depends on:
- Status: PENDING

## TASK_004: Write tests for auth module
- [ ] Create test_auth_handler.py
- [ ] Cover login/logout flows (positive + negative)
- [ ] Test JWT validation and expiration
- Depends on: TASK_001, TASK_003
- Status: PENDING
