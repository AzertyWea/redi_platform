import sys, random
sys.path.insert(0, ".")
from app import create_app, db
from app.models import Course, SchoolClass, ScheduleEntry
from datetime import time as dtime

app = create_app()
app.app_context().push()

# Clear any existing schedule to avoid duplicates on re-run
deleted = ScheduleEntry.query.delete()
db.session.commit()
print(f"Cleared {deleted} old schedule entries")

days = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
slots = [
    (dtime(8,0), dtime(10,0)),
    (dtime(10,0), dtime(12,0)),
    (dtime(13,0), dtime(15,0)),
    (dtime(15,0), dtime(17,0)),
]
rooms = ["Room A101","Room A102","Room A103","Room B201","Room B202",
         "Room B203","Room C301","Room C302","Amphitheater 1","Amphitheater 2"]

# busy[(day, slot_index)] = set of teacher_ids or class_ids currently occupied
busy_teacher = {}
busy_class = {}

def is_free(day, slot_idx, teacher_id, class_id):
    key = (day, slot_idx)
    if teacher_id in busy_teacher.get(key, set()):
        return False
    if class_id in busy_class.get(key, set()):
        return False
    return True

def mark_busy(day, slot_idx, teacher_id, class_id):
    key = (day, slot_idx)
    busy_teacher.setdefault(key, set()).add(teacher_id)
    busy_class.setdefault(key, set()).add(class_id)

classes = SchoolClass.query.all()
pairs = []
for cls in classes:
    for course in cls.courses:
        pairs.append((cls, course))

random.shuffle(pairs)

created = 0
skipped = 0
for cls, course in pairs:
    if not course.teacher_id:
        skipped += 1
        continue
    placed = False
    slot_order = list(range(len(slots)))
    day_order = list(days)
    random.shuffle(slot_order)
    random.shuffle(day_order)
    for day in day_order:
        for slot_idx in slot_order:
            if is_free(day, slot_idx, course.teacher_id, cls.id):
                start, end = slots[slot_idx]
                entry = ScheduleEntry(
                    course_id=course.id,
                    class_group_id=cls.id,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    room=random.choice(rooms),
                    academic_year="2026-2027",
                    semester_number=course.semester_number,
                    is_active=True
                )
                db.session.add(entry)
                mark_busy(day, slot_idx, course.teacher_id, cls.id)
                created += 1
                placed = True
                break
        if placed:
            break
    if not placed:
        skipped += 1

db.session.commit()
print(f"Schedule entries created: {created}")
print(f"Skipped (no free slot or no teacher): {skipped}")
print("=== AUTO TIMETABLE COMPLETE ===")
