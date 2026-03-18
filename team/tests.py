from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .admin import HealthDataAdmin, TeamMemberAdmin, _set_user_role
from .logic import build_region_priority_map, rank_isolation_centers
from .models import (
    DiseaseType,
    DoctorProfile,
    DoctorSpecialty,
    HealthData,
    IsolationCenter,
    Region,
    TeamMember,
)


class CustomLoginRedirectTests(TestCase):
    def test_superuser_redirects_to_admin(self):
        User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            "/login/",
            {"username": "superadmin", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/")

    def test_admin_group_user_redirects_to_admin(self):
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        user = User.objects.create_user(
            username="admin_group_user",
            password="StrongPass123!",
        )
        user.groups.add(admin_group)

        response = self.client.post(
            "/login/",
            {"username": "admin_group_user", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/")

    def test_regular_user_redirects_to_dashboard(self):
        User.objects.create_user(
            username="regular_user",
            password="StrongPass123!",
        )

        response = self.client.post(
            "/login/",
            {"username": "regular_user", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")


class UserRoleAssignmentTests(TestCase):
    def test_set_user_role_replaces_existing_role_groups(self):
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        doctor_group, _ = Group.objects.get_or_create(name="Doctor")
        viewer_group, _ = Group.objects.get_or_create(name="Viewer")
        extra_group, _ = Group.objects.get_or_create(name="Extra")

        user = User.objects.create_user(username="role_user", password="StrongPass123!")
        user.groups.add(doctor_group, viewer_group, extra_group)

        updated = _set_user_role(User.objects.filter(id=user.id), "Admin")
        user.refresh_from_db()

        self.assertEqual(updated, 1)
        self.assertTrue(user.groups.filter(id=admin_group.id).exists())
        self.assertFalse(user.groups.filter(id=doctor_group.id).exists())
        self.assertFalse(user.groups.filter(id=viewer_group.id).exists())
        self.assertTrue(user.groups.filter(id=extra_group.id).exists())

    def test_set_doctor_role_creates_profile(self):
        Group.objects.get_or_create(name="Doctor")
        user = User.objects.create_user(username="doctor_profile_user", password="StrongPass123!")

        _set_user_role(User.objects.filter(id=user.id), "Doctor")

        self.assertTrue(DoctorProfile.objects.filter(user=user).exists())


class DoctorScopedAdminTests(TestCase):
    def setUp(self):
        doctor_group, _ = Group.objects.get_or_create(name="Doctor")
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

        self.doctor_user = User.objects.create_user(username="doctor_1", password="StrongPass123!")
        self.doctor_user.groups.add(doctor_group)
        self.other_doctor = User.objects.create_user(username="doctor_2", password="StrongPass123!")
        self.other_doctor.groups.add(doctor_group)

        specialty, _ = DoctorSpecialty.objects.get_or_create(name="Kardiolog")
        DoctorProfile.objects.get_or_create(user=self.doctor_user, defaults={"specialty": specialty, "room": "12A"})
        DoctorProfile.objects.get_or_create(user=self.other_doctor, defaults={"specialty": specialty, "room": "13B"})

        disease, _ = DiseaseType.objects.get_or_create(name="Gripp", defaults={"isolation_required": True})
        self.my_patient = TeamMember.objects.create(
            full_name="Ali Valiyev",
            age=28,
            position="Muhandis",
            disease_type=disease,
            assigned_doctor=self.doctor_user,
            status="kuzatuv",
        )
        self.other_patient = TeamMember.objects.create(
            full_name="Hasan Qodirov",
            age=34,
            position="Operator",
            disease_type=disease,
            assigned_doctor=self.other_doctor,
            status="davolanish",
        )

        HealthData.objects.create(member=self.my_patient, entered_by=self.doctor_user, temperature=36.8)
        HealthData.objects.create(member=self.other_patient, entered_by=self.other_doctor, temperature=38.2, symptoms=True)

        self.team_admin = TeamMemberAdmin(TeamMember, self.admin_site)
        self.health_admin = HealthDataAdmin(HealthData, self.admin_site)

    def _request_for(self, user):
        request = self.factory.get("/admin/")
        request.user = user
        return request

    def test_doctor_only_sees_own_patients_in_team_admin(self):
        request = self._request_for(self.doctor_user)

        queryset = self.team_admin.get_queryset(request)

        self.assertQuerySetEqual(queryset.order_by("id"), [self.my_patient], transform=lambda obj: obj)

    def test_doctor_only_sees_own_health_records(self):
        request = self._request_for(self.doctor_user)

        queryset = self.health_admin.get_queryset(request)

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().member, self.my_patient)

    def test_doctor_member_field_is_limited_to_own_patients(self):
        request = self._request_for(self.doctor_user)
        formfield = self.health_admin.formfield_for_foreignkey(HealthData._meta.get_field("member"), request)

        self.assertQuerySetEqual(
            formfield.queryset.order_by("id"),
            [self.my_patient],
            transform=lambda obj: obj,
        )

    def test_doctor_cannot_save_other_doctor_patient_record(self):
        request = self._request_for(self.doctor_user)
        health = HealthData(member=self.other_patient, temperature=37.0)

        with self.assertRaises(PermissionDenied):
            self.health_admin.save_model(request, health, form=None, change=False)

    def test_doctor_saved_record_tracks_entered_by(self):
        request = self._request_for(self.doctor_user)
        health = HealthData(member=self.my_patient, temperature=37.4)

        self.health_admin.save_model(request, health, form=None, change=False)

        self.assertEqual(health.entered_by, self.doctor_user)
        self.assertTrue(HealthData.objects.filter(id=health.id, entered_by=self.doctor_user).exists())


class DoctorDashboardAndPatientDetailTests(TestCase):
    def setUp(self):
        doctor_group, _ = Group.objects.get_or_create(name="Doctor")
        self.doctor_user = User.objects.create_user(username="doctor_dashboard", password="StrongPass123!")
        self.doctor_user.groups.add(doctor_group)
        self.other_doctor = User.objects.create_user(username="outsider", password="StrongPass123!")
        self.other_doctor.groups.add(doctor_group)

        specialty, _ = DoctorSpecialty.objects.get_or_create(name="Nevrolog")
        DoctorProfile.objects.get_or_create(user=self.doctor_user, defaults={"specialty": specialty, "room": "9C"})
        DoctorProfile.objects.get_or_create(user=self.other_doctor, defaults={"specialty": specialty, "room": "10A"})

        region_a, _ = Region.objects.get_or_create(name="Samarqand", defaults={"code": "SAM"})
        region_b, _ = Region.objects.get_or_create(name="Navoiy", defaults={"code": "NAV"})
        disease, _ = DiseaseType.objects.get_or_create(name="Bronxit", defaults={"isolation_required": False})
        other_disease, _ = DiseaseType.objects.get_or_create(name="Allergiya", defaults={"isolation_required": False})
        self.my_patient = TeamMember.objects.create(
            full_name="Gulnoza Karimova",
            age=31,
            position="Operator",
            region=region_a,
            disease_type=disease,
            assigned_doctor=self.doctor_user,
            status="davolanish",
            notes="Qayta korik kerak.",
        )
        self.second_patient = TeamMember.objects.create(
            full_name="Gulbahor Saidova",
            age=29,
            position="Laborant",
            region=region_a,
            disease_type=other_disease,
            assigned_doctor=self.doctor_user,
            status="barqaror",
            notes="Nazorat yakunlandi.",
        )
        self.other_patient = TeamMember.objects.create(
            full_name="Dilshod Ergashev",
            age=42,
            position="Manager",
            region=region_b,
            disease_type=disease,
            assigned_doctor=self.other_doctor,
            status="kuzatuv",
        )

        HealthData.objects.create(
            member=self.my_patient,
            entered_by=self.doctor_user,
            temperature=38.1,
            symptoms=True,
            close_contact=True,
            chronic_disease=True,
        )
        HealthData.objects.create(member=self.my_patient, entered_by=self.doctor_user, temperature=37.2)
        HealthData.objects.create(member=self.second_patient, entered_by=self.doctor_user, temperature=36.7)
        HealthData.objects.create(member=self.other_patient, entered_by=self.other_doctor, temperature=36.9)

        self.center_a = IsolationCenter.objects.create(
            name="Samarqand Markaz 1",
            region=region_a,
            capacity=120,
            occupancy_rate=30,
            readiness_score=9,
            infrastructure_score=8,
            travel_time_minutes=18,
            is_active=True,
        )
        self.center_b = IsolationCenter.objects.create(
            name="Navoiy Markaz 2",
            region=region_b,
            capacity=150,
            occupancy_rate=75,
            readiness_score=6,
            infrastructure_score=6,
            travel_time_minutes=50,
            is_active=True,
        )

    def test_doctor_dashboard_contains_personal_context(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_doctor_dashboard"])
        self.assertEqual(response.context["patient_summary"]["total"], 2)
        self.assertEqual(response.context["doctor_focus"]["patient_total"], 2)
        self.assertContains(response, "Mening panelim")
        self.assertContains(response, self.my_patient.full_name)
        self.assertNotContains(response, self.other_patient.full_name)

    def test_doctor_dashboard_filters_by_search_and_status(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("dashboard"), {"q": "Gulbahor", "status": "barqaror"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["patient_summary"]["total"], 1)
        self.assertEqual(response.context["active_filters"]["q"], "Gulbahor")
        self.assertEqual(response.context["active_filters"]["status"], "barqaror")
        self.assertContains(response, self.second_patient.full_name)
        self.assertNotContains(response, self.my_patient.full_name)

    def test_assigned_doctor_can_open_patient_detail(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("patient_detail", args=[self.my_patient.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.my_patient.full_name)
        self.assertContains(response, "Bemor kartasi")
        self.assertContains(response, "Qayta korik kerak")
        self.assertContains(response, "Izohni saqlash")

    def test_assigned_doctor_can_update_patient_notes_inline(self):
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("patient_detail", args=[self.my_patient.id]),
            {"notes": "Yangilangan tavsiya va dori rejasi."},
            follow=True,
        )

        self.my_patient.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.my_patient.notes, "Yangilangan tavsiya va dori rejasi.")
        self.assertContains(response, "Izoh yangilandi")
        self.assertContains(response, "Yangilangan tavsiya va dori rejasi")

    def test_other_doctor_cannot_open_foreign_patient_detail(self):
        self.client.force_login(self.other_doctor)

        response = self.client.get(reverse("patient_detail", args=[self.my_patient.id]))

        self.assertEqual(response.status_code, 404)

    def test_dashboard_contains_ranked_isolation_centers(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        rankings = response.context["center_rankings"]
        self.assertTrue(rankings)
        self.assertEqual(rankings[0]["center"].id, self.center_a.id)
        self.assertContains(response, "Fuzzy MCDM")


class IsolationCenterRankingLogicTests(TestCase):
    def test_region_priority_map_normalizes_distribution(self):
        rows = [
            {"member__region_id": 1, "total": 3},
            {"member__region_id": 2, "total": 1},
        ]

        result = build_region_priority_map(rows)

        self.assertEqual(result[1], 0.75)
        self.assertEqual(result[2], 0.25)

    def test_rank_isolation_centers_orders_by_score(self):
        region = Region.objects.create(name="Buxoro", code="BUX")
        better = IsolationCenter.objects.create(
            name="Center Better",
            region=region,
            capacity=100,
            occupancy_rate=20,
            readiness_score=9,
            infrastructure_score=9,
            travel_time_minutes=15,
            is_active=True,
        )
        weaker = IsolationCenter.objects.create(
            name="Center Weaker",
            region=region,
            capacity=100,
            occupancy_rate=80,
            readiness_score=4,
            infrastructure_score=4,
            travel_time_minutes=70,
            is_active=True,
        )

        rankings = rank_isolation_centers(
            IsolationCenter.objects.filter(id__in=[better.id, weaker.id]),
            {region.id: 1.0},
        )

        self.assertEqual(rankings[0]["center"].id, better.id)
        self.assertGreater(rankings[0]["score"], rankings[1]["score"])
