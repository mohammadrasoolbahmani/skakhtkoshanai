import json
import re
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import (
    CourseSettings, RegistrationRequest, Student, 
    Attendance, SessionDayNote, StudentAchievement, format_shamsi
)


def normalize_phone(phone_str):
    if not phone_str:
        return ""
    fa = '۰۱۲۳۴۵۶۷۸۹'
    ar = '٠١٢٣٤٥٦٧٨٩'
    s = str(phone_str)
    for i in range(10):
        s = s.replace(fa[i], str(i)).replace(ar[i], str(i))
    cleaned = re.sub(r'[\s\-\(\)\+]', '', s)
    if cleaned.startswith('98'):
        cleaned = '0' + cleaned[2:]
    return cleaned


def index_view(request):
    """Serve the ai-learn application page."""
    settings = CourseSettings.get_settings()
    return render(request, 'ai-learn.html', {
        'settings': settings
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_register(request):
    """Handle student registration with receipt upload and family discount."""
    try:
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        phone_raw = request.POST.get('phone', '').strip()
        age_raw = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', '').strip()
        education_level = request.POST.get('level', '').strip()
        password = request.POST.get('password', '').strip()
        tracking_code = request.POST.get('trackingCode', '').strip()
        reg_type = request.POST.get('registrationType', 'regular').strip()
        receipt_file = request.FILES.get('receipt_image')

        errors = {}
        if not first_name:
            errors['firstName'] = 'نام را وارد نمایید.'
        if not last_name:
            errors['lastName'] = 'نام خانوادگی را وارد نمایید.'

        phone = normalize_phone(phone_raw)
        if not re.match(r'^09\d{9}$', phone):
            errors['phone'] = 'شماره موبایل معتبر ۱۱ رقمی وارد نمایید (مانند ۰۹۱۲۳۴۵۶۷۸۹).'
        else:
            if Student.objects.filter(phone=phone, is_active=True).exists():
                errors['phone'] = 'این شماره قبلاً ثبت‌نام شده و حساب آن فعال است. لطفاً وارد شوید.'
            elif RegistrationRequest.objects.filter(phone=phone, status='pending').exists():
                errors['phone'] = 'برای این شماره قبلاً درخواستی ثبت شده و در انتظار تایید منشی است.'

        try:
            age = int(age_raw)
            if age < 10 or age > 99:
                errors['age'] = 'سن باید بین ۱۰ تا ۹۹ سال باشد.'
        except (ValueError, TypeError):
            errors['age'] = 'سن را به صورت عدد معتبر وارد کنید.'

        if gender not in ['male', 'female']:
            errors['gender'] = 'جنسیت را انتخاب نمایید.'

        if not education_level:
            errors['level'] = 'مقطع تحصیلی را انتخاب نمایید.'

        if not password or len(password) < 6:
            errors['password'] = 'رمز عبور حداقل باید ۶ کاراکتر باشد.'

        if not receipt_file:
            errors['receipt'] = 'بارگذاری تصویر فیش یا رسید واریزی الزامی است.'

        if errors:
            return JsonResponse({'success': False, 'errors': errors, 'message': 'لطفاً فیلدهای الزامی را به درستی تکمیل نمایید.'}, status=400)

        settings = CourseSettings.get_settings()
        fee = settings.family_fee_amount if reg_type == 'family' else settings.fee_amount

        req_obj = RegistrationRequest.objects.create(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            age=age,
            gender=gender,
            education_level=education_level,
            requested_password=password,
            registration_type=reg_type,
            fee_amount=fee,
            tracking_code=tracking_code or '—',
            receipt_image=receipt_file,
            status='pending'
        )

        return JsonResponse({
            'success': True,
            'message': 'درخواست ثبت‌نام شما با موفقیت ثبت شد و رسید واریزی برای بررسی منشی ارسال گردید.',
            'request_id': req_obj.id,
            'receipt_url': req_obj.receipt_image.url if req_obj.receipt_image else None,
            'student_name': f"{req_obj.first_name} {req_obj.last_name}",
            'fee_amount': fee
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'خطای سرور: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """Handle user login for secretary or student."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        username_raw = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username_raw or not password:
            return JsonResponse({'success': False, 'message': 'نام کاربری و رمز عبور را وارد نمایید.'}, status=400)

        # Secretary Login
        if username_raw == 'rasool' and password == 'rasool123':
            return JsonResponse({
                'success': True,
                'role': 'secretary',
                'user': {
                    'name': 'منشی دبیرستان سخت‌کوشان',
                    'username': 'rasool'
                }
            })

        # Approved Student Login
        phone = normalize_phone(username_raw)
        student = Student.objects.filter(phone=phone, is_active=True).first()
        if student:
            if student.password == password:
                return JsonResponse({
                    'success': True,
                    'role': 'student',
                    'user': {
                        'id': student.id,
                        'name': f"{student.first_name} {student.last_name}",
                        'phone': student.phone,
                        'level': student.education_level,
                        'age': student.age,
                        'approved_at': format_shamsi(student.approved_at)
                    }
                })
            else:
                return JsonResponse({'success': False, 'message': 'رمز عبور وارد شده نادرست است.'}, status=401)

        # Pending check
        pending_req = RegistrationRequest.objects.filter(phone=phone, status='pending').first()
        if pending_req:
            fee_str = f"{pending_req.fee_amount:,} تومان"
            return JsonResponse({
                'success': False,
                'code': 'PENDING',
                'message': f'رسید واریزی شما ({fee_str}) ارسال شده و در انتظار بررسی و تایید منشی دبیرستان است. پس از تایید منشی، حساب شما فعال خواهد شد.'
            }, status=403)

        # Rejected check
        rejected_req = RegistrationRequest.objects.filter(phone=phone, status='rejected').first()
        if rejected_req:
            return JsonResponse({
                'success': False,
                'code': 'REJECTED',
                'message': 'درخواست ثبت‌نام شما تایید نشد یا لغو گردید. لطفاً با دفتر آموزش دبیرستان سخت‌کوشان تماس بگیرید.'
            }, status=403)

        return JsonResponse({'success': False, 'message': 'نام کاربری یا رمز عبور اشتباه است، یا هنوز حسابی ثبت نشده است.'}, status=404)

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'خطا: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def api_secretary_requests(request):
    """List registration requests for secretary."""
    status_filter = request.GET.get('status', 'all')
    queryset = RegistrationRequest.objects.all()

    if status_filter in ['pending', 'approved', 'rejected']:
        queryset = queryset.filter(status=status_filter)

    data = []
    for req in queryset:
        reg_type_label = 'خانواده (نصف قیمت)' if req.registration_type == 'family' else 'عادی'
        data.append({
            'id': req.id,
            'firstName': req.first_name,
            'lastName': req.last_name,
            'phone': req.phone,
            'age': req.age,
            'gender': req.gender,
            'level': req.education_level,
            'requestedPassword': req.requested_password,
            'registrationType': req.registration_type,
            'registrationTypeLabel': reg_type_label,
            'feeAmount': req.fee_amount,
            'trackingCode': req.tracking_code or '—',
            'receiptUrl': req.receipt_image.url if req.receipt_image else None,
            'status': req.status,
            'createdAt': format_shamsi(req.created_at),
            'approvedAt': format_shamsi(req.approved_at),
        })

    all_reqs = RegistrationRequest.objects.all()
    approved_students = Student.objects.filter(is_active=True)
    total_revenue = sum(s.fee_amount for s in approved_students)

    stats = {
        'pending': all_reqs.filter(status='pending').count(),
        'approved': approved_students.count(),
        'rejected': all_reqs.filter(status='rejected').count(),
        'totalRevenue': total_revenue
    }

    return JsonResponse({'success': True, 'requests': data, 'stats': stats})


@csrf_exempt
@require_http_methods(["POST"])
def api_approve_request(request, request_id):
    """Approve request and activate student account."""
    try:
        req_obj = get_object_or_404(RegistrationRequest, id=request_id)
        if req_obj.status != 'pending':
            return JsonResponse({'success': False, 'message': 'این درخواست قبلاً تعیین وضعیت شده است.'}, status=400)

        req_obj.status = 'approved'
        req_obj.approved_at = timezone.now()
        req_obj.save()

        student, created = Student.objects.get_or_create(
            phone=req_obj.phone,
            defaults={
                'first_name': req_obj.first_name,
                'last_name': req_obj.last_name,
                'password': req_obj.requested_password,
                'age': req_obj.age,
                'gender': req_obj.gender,
                'education_level': req_obj.education_level,
                'registration_type': req_obj.registration_type,
                'registration_request': req_obj,
                'receipt_image': req_obj.receipt_image,
                'tracking_code': req_obj.tracking_code,
                'fee_amount': req_obj.fee_amount,
                'is_active': True,
                'approved_at': req_obj.approved_at
            }
        )
        if not created:
            student.is_active = True
            student.password = req_obj.requested_password
            student.fee_amount = req_obj.fee_amount
            student.registration_type = req_obj.registration_type
            student.save()

        return JsonResponse({
            'success': True,
            'message': f'حساب دانش‌آموز ({student.first_name} {student.last_name}) با موفقیت تایید و فعال شد.',
            'student_id': student.id
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_reject_request(request, request_id):
    """Reject request."""
    try:
        req_obj = get_object_or_404(RegistrationRequest, id=request_id)
        if req_obj.status != 'pending':
            return JsonResponse({'success': False, 'message': 'این درخواست قبلاً تعیین وضعیت شده است.'}, status=400)

        req_obj.status = 'rejected'
        req_obj.rejected_at = timezone.now()
        req_obj.save()

        return JsonResponse({'success': True, 'message': 'درخواست ثبت‌نام لغو / رد شد.'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_delete_student(request, student_id):
    """Delete a student and their records."""
    try:
        student = get_object_or_404(Student, id=student_id)
        st_name = f"{student.first_name} {student.last_name}"
        phone = student.phone
        student.delete()
        RegistrationRequest.objects.filter(phone=phone).delete()

        return JsonResponse({
            'success': True,
            'message': f'دانش‌آموز «{st_name}» با موفقیت از سیستم حذف شد.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def api_students_list(request):
    """List approved students with attendances and achievements count."""
    search_q = request.GET.get('q', '').strip()
    queryset = Student.objects.filter(is_active=True)

    if search_q:
        norm_q = normalize_phone(search_q)
        queryset = queryset.filter(
            models.Q(first_name__icontains=search_q) |
            models.Q(last_name__icontains=search_q) |
            models.Q(phone__icontains=norm_q)
        )

    settings = CourseSettings.get_settings()
    data = []
    for st in queryset:
        attendances = {
            att.session_number: {
                'status': att.status,
                'note': att.note or ''
            } 
            for att in st.attendances.all()
        }
        achievements_count = st.achievements.count()

        data.append({
            'id': st.id,
            'firstName': st.first_name,
            'lastName': st.last_name,
            'phone': st.phone,
            'age': st.age,
            'gender': st.gender,
            'level': st.education_level,
            'registrationType': st.registration_type,
            'feeAmount': st.fee_amount,
            'receiptUrl': st.receipt_image.url if st.receipt_image else None,
            'trackingCode': st.tracking_code or '—',
            'approvedAt': format_shamsi(st.approved_at),
            'attendances': attendances,
            'achievementsCount': achievements_count
        })

    session_notes_dict = {
        sn.session_number: {
            'date_shamsi': sn.date_shamsi or '',
            'topic_or_note': sn.topic_or_note or ''
        }
        for sn in SessionDayNote.objects.all()
    }

    return JsonResponse({
        'success': True,
        'students': data,
        'sessionsCount': settings.sessions_count,
        'sessionNotes': session_notes_dict
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_attendance_toggle(request):
    """Toggle attendance status and optionally save note for session."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        student_id = data.get('student_id')
        session_num = int(data.get('session_number'))
        note = data.get('note', None)

        student = get_object_or_404(Student, id=student_id)
        att = Attendance.objects.filter(student=student, session_number=session_num).first()

        if note is not None and not data.get('toggle_status', False):
            if not att:
                att = Attendance.objects.create(student=student, session_number=session_num, status='present', note=note)
            else:
                att.note = note
                att.save()
            return JsonResponse({'success': True, 'session_number': session_num, 'status': att.status, 'note': att.note})

        if not att:
            att = Attendance.objects.create(student=student, session_number=session_num, status='present', note=note or '')
            next_state = 'present'
        elif att.status == 'present':
            att.status = 'absent'
            if note is not None:
                att.note = note
            att.save()
            next_state = 'absent'
        else:
            att.delete()
            next_state = 'none'

        return JsonResponse({
            'success': True, 
            'session_number': session_num, 
            'status': next_state,
            'note': att.note if (next_state != 'none' and att) else ''
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_save_session_day_note(request):
    """Save daily note/topic for a working day/session."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        session_number = int(data.get('session_number'))
        date_shamsi = data.get('date_shamsi', '').strip()
        topic_or_note = data.get('topic_or_note', '').strip()

        obj, created = SessionDayNote.objects.get_or_create(
            session_number=session_number,
            defaults={'date_shamsi': date_shamsi, 'topic_or_note': topic_or_note}
        )
        if not created:
            obj.date_shamsi = date_shamsi
            obj.topic_or_note = topic_or_note
            obj.save()

        return JsonResponse({
            'success': True,
            'message': f'یادداشت جلسه {session_number} با موفقیت ذخیره شد.',
            'session_number': session_number,
            'date_shamsi': obj.date_shamsi,
            'topic_or_note': obj.topic_or_note
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_upload_achievement(request, student_id):
    """Upload a project/achievement for a specific session by student."""
    try:
        student = get_object_or_404(Student, id=student_id, is_active=True)
        session_num = int(request.POST.get('session_number', 1))
        title = request.POST.get('title', '').strip() or f'پروژه جلسه {session_num}'
        student_notes = request.POST.get('student_notes', '').strip()
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return JsonResponse({'success': False, 'message': 'هیچ فایلی برای بارگذاری انتخاب نشده است.'}, status=400)

        size_bytes = uploaded_file.size
        if size_bytes < 1024:
            size_str = f"{size_bytes} بایت"
        elif size_bytes < 1024 * 1024:
            size_str = f"{round(size_bytes / 1024, 1)} کیلوبایت"
        else:
            size_str = f"{round(size_bytes / (1024 * 1024), 2)} مگابایت"

        item = StudentAchievement.objects.create(
            student=student,
            session_number=session_num,
            title=title,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size_str=size_str,
            student_notes=student_notes
        )

        return JsonResponse({
            'success': True,
            'message': 'دستاورد و پروژه شما با موفقیت برای این جلسه بارگذاری شد.',
            'achievement': {
                'id': item.id,
                'session_number': item.session_number,
                'title': item.title,
                'file_name': item.file_name,
                'file_size': item.file_size_str,
                'file_url': item.file.url,
                'uploaded_at': format_shamsi(item.uploaded_at),
                'student_notes': item.student_notes
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'خطا در بارگذاری: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_delete_achievement(request, achievement_id):
    """Delete an achievement."""
    try:
        item = get_object_or_404(StudentAchievement, id=achievement_id)
        item.file.delete(save=False)
        item.delete()
        return JsonResponse({'success': True, 'message': 'فایل دستاورد با موفقیت حذف شد.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def api_student_dashboard(request, student_id):
    """Dashboard API for a student."""
    student = get_object_or_404(Student, id=student_id, is_active=True)
    settings = CourseSettings.get_settings()

    attendances = {
        att.session_number: {
            'status': att.status,
            'note': att.note or ''
        }
        for att in student.attendances.all()
    }

    session_notes = {
        sn.session_number: {
            'date_shamsi': sn.date_shamsi or '',
            'topic_or_note': sn.topic_or_note or ''
        }
        for sn in SessionDayNote.objects.all()
    }

    achievements = [
        {
            'id': ach.id,
            'session_number': ach.session_number,
            'title': ach.title,
            'file_name': ach.file_name,
            'file_size': ach.file_size_str,
            'file_url': ach.file.url,
            'uploaded_at': format_shamsi(ach.uploaded_at),
            'student_notes': ach.student_notes or ''
        }
        for ach in student.achievements.all()
    ]

    return JsonResponse({
        'success': True,
        'student': {
            'id': student.id,
            'firstName': student.first_name,
            'lastName': student.last_name,
            'phone': student.phone,
            'age': student.age,
            'gender': student.gender,
            'level': student.education_level,
            'registrationType': student.registration_type,
            'feeAmount': student.fee_amount,
            'approvedAt': format_shamsi(student.approved_at),
            'receiptUrl': student.receipt_image.url if student.receipt_image else None
        },
        'course': {
            'title': settings.course_title,
            'sessionsCount': settings.sessions_count,
            'feeAmount': settings.fee_amount,
            'familyFeeAmount': settings.family_fee_amount,
            'cardNumber': settings.card_number,
            'cardHolder': settings.card_holder
        },
        'attendances': attendances,
        'sessionNotes': session_notes,
        'achievements': achievements
    })


@require_http_methods(["GET"])
def api_course_settings(request):
    """Get course settings."""
    settings = CourseSettings.get_settings()
    return JsonResponse({
        'success': True,
        'course_title': settings.course_title,
        'fee_amount': settings.fee_amount,
        'family_fee_amount': settings.family_fee_amount,
        'sessions_count': settings.sessions_count,
        'card_number': settings.card_number,
        'card_holder': settings.card_holder
    })
