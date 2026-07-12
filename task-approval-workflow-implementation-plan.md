# Task Approval Workflow System — Implementation Plan

## 1. Tech Stack (pinned versions for production parity)

| Layer | Choice |
|---|---|
| Backend | Django 5.0.x + Django REST Framework 3.15.x |
| Auth | `djangorestframework-simplejwt` (JWT, access + refresh, rotation, blacklist) |
| DB | PostgreSQL 16 |
| Cache/Broker | Redis 7 |
| Async tasks | Celery 5.4 + Celery Beat (periodic jobs) |
| Frontend | React 18 + Vite + Axios + React Query + React Router |
| Custom admin dashboard | Django Templates (server-rendered, separate from DRF, separate from React app) |
| Containerization | Docker + Docker Compose (multi-stage builds) |
| Web server | Gunicorn + Nginx (reverse proxy, static/media serving) |
| Testing | pytest + pytest-django + factory_boy + coverage |
| Filtering/Search | django-filter + DRF SearchFilter/OrderingFilter |
| Docs | drf-spectacular (OpenAPI/Swagger) |

Reasoning: SimpleJWT is the DRF-native standard (avoids reinventing auth). django-filter + DRF's built-in filters cover 95% of filtering needs without custom query-building. drf-spectacular gives auto-generated API docs for the React team.

---

## 2. Repository / Project Structure

```
task-approval-system/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   ├── config/                     # project settings package
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   └── prod.py
│   │   ├── celery.py
│   │   ├── urls.py
│   │   └── wsgi.py / asgi.py
│   ├── apps/
│   │   ├── users/                  # custom User model, roles, JWT views
│   │   ├── tasks/                  # Task, TaskComment, TaskAttachment, TaskStatusHistory
│   │   ├── notifications/          # Notification model + Celery tasks
│   │   ├── dashboard/              # custom Django-template admin panel (staff/manager/superadmin views)
│   │   └── core/                   # shared permissions, mixins, pagination, exceptions
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── api/                    # axios instance, interceptors (JWT refresh)
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── tasks/
│   │   │   └── notifications/
│   │   ├── routes/
│   │   └── components/
│   └── nginx.conf                  # serves built React app in prod
└── nginx/
    └── nginx.conf                  # reverse proxy: /api -> backend, /admin-panel -> django templates, / -> react build
```

Two UIs, one backend: the React app talks only to DRF (`/api/v1/...`). The custom Django-template dashboard is a **separate app** (`apps/dashboard`) that reuses the same models/services but renders server-side HTML for staff/manager/superadmin — it should NOT duplicate business logic; it calls the same service-layer functions the DRF views call.

---

## 3. Data Models

### 3.1 `users.User` (extends `AbstractUser`)
```python
class Role(models.TextChoices):
    STAFF = "STAFF", "Staff"
    MANAGER = "MANAGER", "Manager"
    SUPERADMIN = "SUPERADMIN", "Super Admin"

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF, db_index=True)
    department = models.CharField(max_length=100, blank=True)
    is_active_employee = models.BooleanField(default=True)

    @property
    def is_manager(self): return self.role in (Role.MANAGER, Role.SUPERADMIN)
    @property
    def is_superadmin(self): return self.role == Role.SUPERADMIN
```
- `role` indexed since every permission check and dashboard filter queries by it.
- `is_superadmin` bypasses all object-level checks (see Permissions section).

### 3.2 `tasks.Task`

> **Assignee & reviewer are both optional at creation time — and reviewer can even be assigned *after* the task has already been submitted.** A task can be created bare (title/description only) and left completely unassigned. Either an assignee or the creator can submit it while still `DRAFT`, and the creator (or superadmin) can attach a reviewer at any point — before submission, or afterwards while the task sits in `SUBMITTED` waiting on someone to review it. This was already achievable schema-wise with `null=True, blank=True` / `blank=True` below — no migration needed — but the workflow rules change: submission is **not** gated on a reviewer being present; instead, the gate moves to the approve/reject step, since that's the point a reviewer actually becomes necessary. See Section 5 for the updated `transition_task()` / new `assign_reviewer()` logic.

```python
class TaskStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"

class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_tasks")
    assignees = models.ManyToManyField(User, related_name="assigned_tasks", blank=True)  # optional; max 2 enforced in serializer/clean(); addable anytime while DRAFT
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="tasks_to_review",
                                  null=True, blank=True, limit_choices_to={"role__in": ["MANAGER", "SUPERADMIN"]})
    # reviewer optional at creation AND while SUBMITTED; only required by the time approve()/reject() is called — see services.py
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.DRAFT, db_index=True)
    priority = models.CharField(max_length=10, choices=[("LOW","Low"),("MEDIUM","Medium"),("HIGH","High")], default="MEDIUM")
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["creator", "status"]),
            models.Index(fields=["reviewer", "status"]),
        ]
        ordering = ["-created_at"]
```
Composite indexes match the two most common queries: "my dashboard tasks by status" and "tasks I need to review."

### 3.3 `tasks.TaskComment`
```python
class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

### 3.4 `tasks.TaskAttachment`
```python
def attachment_upload_path(instance, filename):
    return f"tasks/{instance.task_id}/attachments/{filename}"

class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=attachment_upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
```
Validate file size/type in serializer (e.g., max 10MB, whitelist extensions) — never trust client-side validation alone.

### 3.5 `tasks.TaskStatusHistory` (audit trail — populated via signals, never written directly by views)
```python
class TaskStatusHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-changed_at"]
```

### 3.6 `notifications.Notification`
```python
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications", db_index=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=30)  # ASSIGNED, SUBMITTED, APPROVED, REJECTED, COMMENT
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 4. Roles & Permission Matrix

| Action | Staff | Manager | Superadmin |
|---|---|---|---|
| Create task (assignee/reviewer optional) | ✅ | ✅ | ✅ |
| Edit task (title/description/priority/etc.) while DRAFT | ✅ (creator only) | ✅ (creator only) | ✅ (any) |
| Assign/reassign up to 2 assignees, anytime while DRAFT | ✅ (creator only) | ✅ (creator only) | ✅ |
| Assign/change reviewer — while `DRAFT` **or** `SUBMITTED` (must pick a Manager/Superadmin) | ✅ (creator only) | ✅ (creator only) | ✅ |
| Submit for approval, while `DRAFT` — no reviewer required at this point | ✅ (creator **or** an assignee) | ✅ (creator or an assignee) | ✅ |
| Approve / Reject — **requires a reviewer to be set on the task** | ❌ | ✅ (only if assigned as reviewer on that task) | ✅ (any task, even reviewer-less, as an override) |
| Comment | ✅ (creator/assignee/reviewer) | same | ✅ |
| Upload attachment | ✅ (creator/assignee) | same | ✅ |
| View audit trail | ✅ (own tasks) | ✅ (own + reviewing) | ✅ (all) |
| Custom dashboard access | limited view | manager view (team tasks, pending reviews) | full view (all users, all tasks, override) |

A task with no assignees and no reviewer is a perfectly valid `DRAFT`, and can even be submitted with no reviewer yet — it just sits as `SUBMITTED` with a **"Needs Reviewer"** state until the creator gets around to assigning one. The dashboard should surface explicit **"Unassigned"** (no assignees/reviewer) and **"Needs Reviewer"** (submitted, no reviewer) filters/counts so nothing silently stalls.

### DRF permission classes (`apps/core/permissions.py`)
```python
class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superadmin

class IsCreatorOrSuperAdmin(BasePermission):
    """General field edits (title, description, assignees, priority, etc.) — DRAFT only."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        return obj.creator_id == request.user.id and obj.status == TaskStatus.DRAFT

class CanSubmitTask(BasePermission):
    """Submit allowed for the creator, any current assignee, or superadmin — while DRAFT."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        if obj.status != TaskStatus.DRAFT:
            return False
        return obj.creator_id == request.user.id or obj.assignees.filter(pk=request.user.id).exists()

class CanAssignReviewer(BasePermission):
    """Assigning/changing the reviewer is allowed for the creator or superadmin,
    while the task is DRAFT or SUBMITTED (i.e. even after it's already been submitted)."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        return obj.creator_id == request.user.id and obj.status in (TaskStatus.DRAFT, TaskStatus.SUBMITTED)

class IsAssignedReviewerOrSuperAdmin(BasePermission):
    """Approve/reject allowed only for the assigned reviewer (must be Manager+) or superadmin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        return obj.reviewer_id == request.user.id and request.user.is_manager
```
Object-level checks are enforced in `get_object()` / `perform_update()`, never trusted from query params alone. Note `CanSubmitTask` and `CanAssignReviewer` are deliberately separate classes from `IsCreatorOrSuperAdmin` — they permit narrower, single-purpose actions (submit; reviewer change) under conditions (assignee identity; `SUBMITTED` status) that general field editing must NOT be opened up to.

### Model-level validation (belt-and-braces, `Task.clean()` / serializer `validate()`)
- `assignees` and `reviewer` are both optional on create — a bare, fully-unassigned `DRAFT` task is valid and expected.
- When a reviewer **is** provided (at creation, or later while `DRAFT`/`SUBMITTED`), it must have `role in (MANAGER, SUPERADMIN)` — enforced by `limit_choices_to` **and** serializer validation (limit_choices_to is only a UI hint in admin, not a DB constraint).
- `assignees.count() <= 2` whenever assignees are set — enforced in serializer `validate_assignees()`, and again in a `clean()` override for defense-in-depth if saved outside DRF (e.g., via the Django template dashboard).
- Reviewer cannot be the creator (avoid self-review) — business rule, confirm with stakeholders but recommended.
- **Submission is not gated on a reviewer.** A `DRAFT` task can move to `SUBMITTED` with `reviewer = NULL`; it simply becomes a "Needs Reviewer" submitted task until the creator assigns one.
- **Approval gate:** `transition_task()` still requires `reviewer_id` to match `actor.id` (or `actor.is_superadmin`) before allowing `APPROVED`/`REJECTED` — so in practice a reviewer-less submitted task just can't be approved/rejected by anyone except a superadmin override until a real reviewer is attached.

---

## 5. Workflow State Machine

```
DRAFT ──submit()──▶ SUBMITTED ──approve()──▶ APPROVED
                        │
                        └──reject()──▶ REJECTED ──reopen()──▶ DRAFT
```

Implemented as explicit service functions rather than scattering `task.status = X; task.save()` across views — this is what makes rules testable and prevents illegal transitions.

`apps/tasks/services.py`:
```python
ALLOWED_TRANSITIONS = {
    TaskStatus.DRAFT: {TaskStatus.SUBMITTED},
    TaskStatus.SUBMITTED: {TaskStatus.APPROVED, TaskStatus.REJECTED},
    TaskStatus.REJECTED: {TaskStatus.DRAFT},
    TaskStatus.APPROVED: set(),  # terminal
}

@transaction.atomic
def transition_task(task: Task, *, to_status: str, actor: User, remarks: str = "") -> Task:
    if to_status not in ALLOWED_TRANSITIONS.get(task.status, set()):
        raise InvalidTransitionError(f"Cannot move task from {task.status} to {to_status}")

    if to_status == TaskStatus.SUBMITTED:
        is_creator = task.creator_id == actor.id
        is_assignee = task.assignees.filter(pk=actor.id).exists()
        if not (is_creator or is_assignee or actor.is_superadmin):
            raise PermissionDenied("Only the creator or an assignee can submit this task.")
        # NOTE: no reviewer check here — a task may be submitted with reviewer=None.
        # It simply waits in SUBMITTED as "Needs Reviewer" until assign_reviewer() is called.

    if to_status in (TaskStatus.APPROVED, TaskStatus.REJECTED):
        if not actor.is_superadmin and (task.reviewer_id != actor.id or not actor.is_manager):
            raise PermissionDenied("Only the assigned reviewer can approve/reject.")
            # If reviewer_id is None, this branch always denies for non-superadmins —
            # i.e. approval is naturally blocked until a reviewer exists, without
            # needing a separate explicit "reviewer required" check.

    task = Task.objects.select_for_update().get(pk=task.pk)  # row lock, avoid race on concurrent approve/reject
    from_status = task.status
    task.status = to_status
    task.save(update_fields=["status", "updated_at"])

    # signal handles TaskStatusHistory + Notification creation (see Signals section)
    task_status_changed.send(sender=Task, task=task, from_status=from_status,
                              to_status=to_status, actor=actor, remarks=remarks)
    return task


@transaction.atomic
def assign_reviewer(task: Task, *, reviewer: User, actor: User) -> Task:
    """Attach or change the reviewer. Allowed while DRAFT or SUBMITTED — this is what
    lets a creator submit a task first and decide on a reviewer afterwards."""
    if task.status not in (TaskStatus.DRAFT, TaskStatus.SUBMITTED):
        raise InvalidTransitionError("Reviewer can only be set while the task is DRAFT or SUBMITTED.")
    if task.creator_id != actor.id and not actor.is_superadmin:
        raise PermissionDenied("Only the creator can assign a reviewer.")
    if not reviewer.is_manager:
        raise ValidationError("Reviewer must be a Manager or Superadmin.")
    if reviewer.id == task.creator_id:
        raise ValidationError("A task's creator cannot also be its reviewer.")

    task = Task.objects.select_for_update().get(pk=task.pk)
    previous_reviewer = task.reviewer
    task.reviewer = reviewer
    task.save(update_fields=["reviewer", "updated_at"])

    reviewer_assigned.send(sender=Task, task=task, reviewer=reviewer,
                            previous_reviewer=previous_reviewer, actor=actor)
    return task
```
`select_for_update()` inside the atomic block prevents two simultaneous approve/reject calls (e.g., double-click, or manager + superadmin acting at once) from both succeeding and producing inconsistent history rows.

Optional: swap this hand-rolled state machine for `django-fsm` if the team wants declarative `@transition` decorators — functionally equivalent for this scope, hand-rolled is preferred here for full control over the permission checks and testability without an extra dependency.

---

## 6. Signals — Audit Trail & Notifications

`apps/tasks/signals.py`:
```python
task_status_changed = django.dispatch.Signal()

@receiver(task_status_changed)
def create_status_history(sender, task, from_status, to_status, actor, remarks, **kwargs):
    TaskStatusHistory.objects.create(
        task=task, from_status=from_status, to_status=to_status,
        changed_by=actor, remarks=remarks,
    )

@receiver(task_status_changed)
def notify_on_status_change(sender, task, from_status, to_status, actor, **kwargs):
    recipients = set(task.assignees.all())
    if task.reviewer_id and to_status == TaskStatus.SUBMITTED:
        recipients.add(task.reviewer)
    if to_status in (TaskStatus.APPROVED, TaskStatus.REJECTED):
        recipients.add(task.creator)
    for user in recipients:
        send_task_notification.delay(user.id, task.id, to_status)  # Celery task


reviewer_assigned = django.dispatch.Signal()

@receiver(reviewer_assigned)
def notify_new_reviewer(sender, task, reviewer, previous_reviewer, actor, **kwargs):
    """Fires whether the reviewer is set before or after submission — covers both
    'assigned at creation' and 'assigned later once the task is already SUBMITTED'."""
    event_type = "REVIEWER_ASSIGNED_SUBMITTED" if task.status == TaskStatus.SUBMITTED else "REVIEWER_ASSIGNED_DRAFT"
    send_task_notification.delay(reviewer.id, task.id, event_type)
```
Also hook `m2m_changed` on `assignees` and `post_save` on `Task` (creation) to fire "assigned" notifications separately from status-transition notifications — keep these as distinct signals so the history table only ever logs actual status transitions, not every field edit.

---

## 7. Celery — Async Notifications & Periodic Jobs

`config/celery.py` — standard app factory, broker = Redis, result backend = Redis (or disable results if not needed, to save memory).

`apps/notifications/tasks.py`:
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_task_notification(self, user_id, task_id, event_type):
    try:
        user = User.objects.get(pk=user_id)
        task = Task.objects.get(pk=task_id)
        Notification.objects.create(recipient=user, task=task, notification_type=event_type,
                                     message=build_message(event_type, task))
        send_mail(...)  # or integrate with a transactional email provider
    except (User.DoesNotExist, Task.DoesNotExist):
        return  # don't retry on missing objects
    except SMTPException as exc:
        raise self.retry(exc=exc)
```
Periodic job (Celery Beat) example: nightly cleanup of read notifications older than 30 days, and a daily digest email of pending reviews per manager.

Worker + beat run as **separate containers** in Docker Compose (see Section 10) so they scale independently of the web process.

---

## 8. Redis Caching — Dashboard Counts

Cache per-user, per-role aggregate counts (draft/submitted/approved/rejected, pending-review count) rather than raw querysets:
```python
def get_dashboard_counts(user: User) -> dict:
    cache_key = f"dashboard:counts:{user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    counts = {
        "draft": Task.objects.filter(creator=user, status=TaskStatus.DRAFT).count(),
        "unassigned": Task.objects.filter(creator=user, status=TaskStatus.DRAFT,
                                           assignees__isnull=True, reviewer__isnull=True).distinct().count(),
        "submitted": Task.objects.filter(creator=user, status=TaskStatus.SUBMITTED).count(),
        "needs_reviewer": Task.objects.filter(creator=user, status=TaskStatus.SUBMITTED,
                                               reviewer__isnull=True).count(),
        "pending_review": Task.objects.filter(reviewer=user, status=TaskStatus.SUBMITTED).count() if user.is_manager else 0,
        "approved": Task.objects.filter(creator=user, status=TaskStatus.APPROVED).count(),
        "rejected": Task.objects.filter(creator=user, status=TaskStatus.REJECTED).count(),
    }
    cache.set(cache_key, counts, timeout=60 * 5)  # 5 min TTL
    return counts
```
Invalidate via a `post_save`/`task_status_changed` receiver that deletes `dashboard:counts:{creator_id}` and `dashboard:counts:{reviewer_id}` whenever a relevant task changes — TTL alone is a safety net, not the primary invalidation strategy.

---

## 9. API Surface (DRF, versioned under `/api/v1/`)

| Endpoint | Method | Notes |
|---|---|---|
| `/auth/register/` | POST | staff/manager only self-register; superadmin created via management command/seed |
| `/auth/login/` | POST | returns access + refresh JWT |
| `/auth/refresh/` | POST | rotates refresh token (blacklist old) |
| `/tasks/` | GET, POST | list (paginated, filterable, searchable) / create |
| `/tasks/{id}/` | GET, PATCH, DELETE | PATCH (title/description/assignees/priority/etc.) only if `IsCreatorOrSuperAdmin` & DRAFT |
| `/tasks/{id}/submit/` | POST | calls `transition_task(to=SUBMITTED)`; permission `CanSubmitTask` (creator, an assignee, or superadmin) |
| `/tasks/{id}/assign-reviewer/` | POST | body: `{"reviewer": <id>}`; calls `assign_reviewer()`; permission `CanAssignReviewer` — works while `DRAFT` **or** `SUBMITTED`, so a reviewer can be attached after the task's already been submitted |
| `/tasks/{id}/approve/` | POST | calls `transition_task(to=APPROVED)` |
| `/tasks/{id}/reject/` | POST | body: `remarks`; calls `transition_task(to=REJECTED)` |
| `/tasks/{id}/comments/` | GET, POST | |
| `/tasks/{id}/attachments/` | GET, POST | multipart upload, size/type validated |
| `/tasks/{id}/history/` | GET | read-only audit trail |
| `/notifications/` | GET | current user's notifications, paginated |
| `/notifications/{id}/read/` | POST | mark read |
| `/dashboard/counts/` | GET | cached aggregate counts, including `unassigned` and `needs_reviewer` |

`PATCH /tasks/{id}/` handles general field edits (title, description, priority, assignees) and is DRAFT-only via `IsCreatorOrSuperAdmin`. Reviewer assignment is deliberately **its own endpoint** (`/assign-reviewer/`) rather than folded into `PATCH`, because it has a different status window (`DRAFT` **or** `SUBMITTED`, not just `DRAFT`) and a different permission class (`CanAssignReviewer`) — keeping it separate avoids accidentally widening the general-edit endpoint's status check just to accommodate one field.

Filtering/search/pagination via `django-filter` `FilterSet` on `status`, `creator`, `reviewer`, `priority`, `due_date` range, plus `search=` (title/description) and `ordering=` (created_at, due_date, priority). Use `CursorPagination` for the task list (stable ordering under concurrent inserts) and standard `PageNumberPagination` elsewhere.

---

## 10. Custom Django-Template Dashboard (`apps/dashboard`)

- Separate from Django's built-in `/admin/` — a purpose-built set of templates at e.g. `/panel/`.
- Role-gated views using a `role_required` decorator/mixin (`LoginRequiredMixin` + custom `RoleRequiredMixin`).
- Staff view: their own tasks + status.
- Manager view: team tasks + a "Pending My Review" queue.
- Superadmin view: all tasks, all users, ability to force-transition/override any task (still routed through `transition_task()` with `actor.is_superadmin` bypass — never a separate code path).
- Reuses `apps/tasks/services.py` and `apps/tasks/selectors.py` (read-query layer) so business logic isn't duplicated between DRF and templates.

---

## 11. Docker Compose (dev) — services

```yaml
services:
  db:            # postgres:16, volume-persisted
  redis:         # redis:7
  backend:       # django + gunicorn (or runserver in dev), depends_on db, redis
  celery_worker: # same image as backend, command: celery -A config worker -l info
  celery_beat:   # same image, command: celery -A config beat -l info
  frontend:      # vite dev server (dev) / nginx serving build (prod)
  nginx:         # reverse proxy, prod only
```
Key practices: multi-stage Dockerfiles (builder + slim runtime), non-root user in containers, `.dockerignore`, health checks on `db`/`redis` with `depends_on: condition: service_healthy`, separate `docker-compose.prod.yml` overlay (Gunicorn workers tuned to CPU count, `DEBUG=False`, Nginx serving `/static/` and `/media/` directly).

---

## 12. Testing Strategy

- **Unit tests** (`apps/tasks/tests/test_services.py`): every entry in `ALLOWED_TRANSITIONS` tested both for the happy path and for each illegal transition (assert `InvalidTransitionError`). Additionally: creating a task with no assignees and no reviewer succeeds and stays `DRAFT`; an **assignee** (not just the creator) can call `transition_task(to=SUBMITTED)` successfully; a random staff user who is neither creator nor assignee cannot submit; submitting a reviewer-less task succeeds (no longer blocked); `assign_reviewer()` succeeds while `DRAFT` and while `SUBMITTED`, but raises `InvalidTransitionError` once `APPROVED`; attempting `approve()`/`reject()` on a `SUBMITTED` task with `reviewer=None` is denied for everyone except a superadmin; assigning a reviewer to an already-`SUBMITTED` task and then having that reviewer approve it succeeds end-to-end.
- **Permission tests**: staff cannot approve; manager not assigned as reviewer cannot approve; creator cannot edit after SUBMITTED; superadmin bypasses all.
- **Signal tests**: assert `TaskStatusHistory` row created with correct `from_status`/`to_status`/`changed_by` on every transition; assert `Notification` created for the right recipients.
- **Concurrency test**: two threads/transactions calling `approve()`/`reject()` simultaneously on the same task — assert only one succeeds (`select_for_update` correctness).
- **API tests** (DRF `APITestCase`): auth flow, CRUD, filters, pagination, file upload validation (reject oversized/blacklisted file types).
- Use `factory_boy` factories for `User`, `Task`, etc., and `pytest-django`'s `django_db` fixture with `--reuse-db` for fast local iteration. Target >90% coverage on `apps/tasks/services.py` and permission classes specifically (the business-critical paths), not just an aggregate repo-wide number.

---

## 13. Security Checklist

- JWT: short-lived access tokens (~15 min), rotating refresh tokens with blacklist on logout/rotation.
- Rate-limit `/auth/login/` (django-ratelimit or DRF throttling) to blunt brute force.
- File upload: validate MIME type by content sniffing (not just extension), cap size, store outside web root, serve via signed/expiring URLs if attachments are sensitive.
- CORS: restrict `CORS_ALLOWED_ORIGINS` to the known React app origin(s), never `CORS_ALLOW_ALL_ORIGINS` in prod.
- All approve/reject/submit endpoints require HTTPS-only cookies or `Authorization: Bearer` header — no CSRF-exempt trust of client-supplied role claims.
- Environment secrets via `.env` + Docker secrets in prod, never committed.

---

## 14. Suggested Build Order (milestones)

1. Scaffolding: Docker Compose skeleton, Postgres+Redis up, Django project boots, health-check endpoint.
2. `users` app: custom User model, JWT auth, role seeding (management command to create a superadmin).
3. `tasks` app: models + migrations + indexes; admin registration for internal debugging.
4. Service layer (`services.py`, `selectors.py`) + state machine + unit tests for transitions (build this **before** wiring views — it's the core business logic).
5. DRF serializers/viewsets/permissions + API tests.
6. Signals: audit trail + notification dispatch (Celery stubbed with `.delay()` calls, worker wired next).
7. Celery + Redis: worker/beat containers, notification sending, dashboard-count caching.
8. React frontend: auth flow, task list/detail, submit/approve/reject actions, comments, attachments.
9. Custom Django-template dashboard: staff/manager/superadmin views reusing selectors/services.
10. Filtering/search/pagination polish, drf-spectacular docs.
11. Full test pass (unit + API + concurrency), coverage report.
12. Production Docker Compose overlay, Nginx, Gunicorn tuning, deployment runbook.

This order front-loads the workflow/permission logic (the highest-risk, most rule-heavy part) and tests it in isolation before any HTTP or UI layer touches it — the cheapest place to catch a broken business rule is in a service-layer unit test, not in a React integration test three weeks later.
