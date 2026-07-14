from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from google_sheets import SCOPES


def connect_drive():
    creds = Credentials.from_service_account_file(
        "credentials/google_service_account.json",
        scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds)


def upload_work_photo(file_path, folder_id="1DLdXDotbndaaKC3cNQW855TTApgkNqv8"):
    drive = connect_drive()

    file_metadata = {
        "name": file_path.split("/")[-1]
    }

    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(file_path)

    result = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name"
    ).execute()

    print("อัปโหลดรูปสำเร็จ:", result["name"])

    return result["id"]
