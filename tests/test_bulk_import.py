import io
import pandas as pd
import pytest
from app.models import User, StudentProfile, Document
from app import db
from app.services.bulk_import import generate_template, preview_import, commit_import

class TestTemplates:
    def test_roster_template(self):
        buf = generate_template("roster")
        assert len(buf.getvalue()) > 1000

    def test_grades_template(self):
        buf = generate_template("grades")
        assert len(buf.getvalue()) > 1000

    def test_documents_template(self):
        buf = generate_template("documents")
        assert len(buf.getvalue()) > 1000

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            generate_template("invalid")

class TestRosterImport:
    @pytest.fixture
    def roster_file(self):
        buf = io.BytesIO()
        df = pd.DataFrame({
            "matricule": ["PTEST01", "PTEST02"],
            "name": ["Pytest Alice", "Pytest Bob"],
            "role": ["student", "student"],
            "department": ["Informatique", "Informatique"],
            "program": ["HND SE", "HND SE"],
            "password": ["test123", "test123"]
        })
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="data")
        buf.seek(0)
        return buf

    def test_preview_valid(self, roster_file, ctx):
        data, err = preview_import(roster_file, "roster")
        assert err is None
        assert data["stats"]["valid"] == 2
        assert data["stats"]["total"] == 2

    def test_commit_creates_users(self, roster_file, ctx):
        data, err = preview_import(roster_file, "roster")
        assert err is None
        result = commit_import(data)
        assert result["created"] == 2
        assert User.query.filter_by(matricule="PTEST01").first() is not None
        assert User.query.filter_by(matricule="PTEST02").first() is not None

    def test_duplicate_skipped(self, roster_file, ctx):
        data, err = preview_import(roster_file, "roster")
        result = commit_import(data)
        assert result["skipped"] == 2

    def test_cleanup(self, ctx):
        for u in User.query.filter(User.matricule.like("PTEST%")).all():
            for p in StudentProfile.query.filter_by(user_id=u.id).all():
                db.session.delete(p)
            db.session.delete(u)
        db.session.commit()
        assert User.query.filter(User.matricule.like("PTEST%")).count() == 0

class TestGradesImport:
    @pytest.fixture
    def grades_file(self):
        buf = io.BytesIO()
        df = pd.DataFrame({
            "matricule": ["S0010", "S0011"],
            "ca_score": [15.5, 14.0],
            "exam_score": [12.0, 11.5],
            "semester_number": [1, 1]
        })
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="data")
        buf.seek(0)
        return buf

    def test_preview(self, grades_file, ctx):
        data, err = preview_import(grades_file, "grades")
        assert err is None
        assert data["stats"]["valid"] == 2

    def test_commit(self, grades_file, ctx):
        data, err = preview_import(grades_file, "grades")
        assert err is None
        result = commit_import(data)
        assert result["created"] == 2

class TestDocumentsImport:
    @pytest.fixture
    def docs_file(self):
        buf = io.BytesIO()
        df = pd.DataFrame({
            "matricule": ["S0010"],
            "doc_type": ["transcript"],
            "filename": ["pytest_report.pdf"]
        })
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="data")
        buf.seek(0)
        return buf

    def test_commit(self, docs_file, ctx):
        before = Document.query.count()
        data, err = preview_import(docs_file, "documents")
        assert err is None
        result = commit_import(data)
        assert result["created"] == 1
        assert Document.query.count() == before + 1
