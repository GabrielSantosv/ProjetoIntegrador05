import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import database


def _configure_temp_db(tmp_path: Path) -> None:
    database.SQLITE_PATH = tmp_path / "owner_scope.db"
    if database.SQLITE_PATH.exists():
        database.SQLITE_PATH.unlink()
    database.ensure_schema()


def test_owner_scoped_records_are_isolated(tmp_path):
    _configure_temp_db(tmp_path)

    user_one = 11
    user_two = 22

    folder_one = database.create_folder("Pasta A", user_one, folder_id="folder-a")
    folder_two = database.create_folder("Pasta B", user_two, folder_id="folder-b")

    assert database.list_folders(user_one) == [folder_one]
    assert database.list_folders(user_two) == [folder_two]
    assert database.get_folder("folder-a", owner_id=user_two) is None

    document_path = tmp_path / "document.pdf"
    document_path.write_text("pdf", encoding="utf-8")
    doc_one = database.create_document("Doc A", str(document_path), folder_id="folder-a", owner_id=user_one)
    doc_two = database.create_document("Doc B", str(document_path), folder_id="folder-b", owner_id=user_two)

    docs_one, total_one = database.list_documents(owner_id=user_one)
    docs_two, total_two = database.list_documents(owner_id=user_two)
    assert total_one == 1
    assert total_two == 1
    assert docs_one[0]["id"] == doc_one
    assert docs_two[0]["id"] == doc_two
    assert database.get_document(doc_two, owner_id=user_one) is None
    assert database.delete_document(doc_two, owner_id=user_one) is False

    image_path = tmp_path / "rg.png"
    image_path.write_text("img", encoding="utf-8")
    rg_one = database.create_rg("rg-a.png", str(image_path), folder_id="folder-a", owner_id=user_one)
    rg_two = database.create_rg("rg-b.png", str(image_path), folder_id="folder-b", owner_id=user_two)

    assert [item["id"] for item in database.list_rgs(owner_id=user_one)] == [rg_one]
    assert [item["id"] for item in database.list_rgs(owner_id=user_two)] == [rg_two]
    assert database.get_rg(rg_two, owner_id=user_one) is None
    assert database.delete_rg(rg_two, owner_id=user_one) is False

    process_path = tmp_path / "process.pdf"
    process_path.write_text("process", encoding="utf-8")
    process_one = database.create_process_document(
        owner_id=user_one,
        folder_id="folder-a",
        process_number="0001234-56.2024.8.26.0100",
        original_filename="process-a.pdf",
        file_path=str(process_path),
    )
    process_two = database.create_process_document(
        owner_id=user_two,
        folder_id="folder-b",
        process_number="0009876-54.2024.8.26.0100",
        original_filename="process-b.pdf",
        file_path=str(process_path),
    )

    assert [item["id"] for item in database.list_process_documents(owner_id=user_one)] == [process_one]
    assert [item["id"] for item in database.list_process_documents(owner_id=user_two)] == [process_two]
    assert database.get_process_document(process_two, owner_id=user_one) is None
    assert database.delete_process_document(process_two, owner_id=user_one) is False
