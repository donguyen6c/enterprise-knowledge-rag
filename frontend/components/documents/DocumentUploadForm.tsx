import {ChangeEvent, FormEvent, useState} from "react";
import {Upload} from "lucide-react";

import {DocumentItem, DocumentUploadPayload, Organization} from "@/lib/api";

type DocumentUploadFormProps = {
  isSystemAdmin: boolean;
  onUpload: (payload: DocumentUploadPayload) => Promise<boolean>;
  organizations: Organization[];
  uploading: boolean;
};

export function DocumentUploadForm({
  isSystemAdmin,
  onUpload,
  organizations,
  uploading
}: DocumentUploadFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<DocumentItem["visibility"]>(
    "ORGANIZATION"
  );
  const [organization, setOrganization] = useState("");

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] || null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      return;
    }

    const succeeded = await onUpload({
      file,
      title: title || file.name.replace(/\.[^.]+$/, ""),
      description,
      visibility,
      organization: isSystemAdmin ? Number(organization) : undefined
    });

    if (succeeded) {
      setFile(null);
      setTitle("");
      setDescription("");
      setVisibility("ORGANIZATION");
      setOrganization("");
      setIsOpen(false);
    }
  }

  if (!isOpen) {
    return (
      <button
        className="primary-button document-upload-trigger"
        onClick={() => setIsOpen(true)}
        type="button"
      >
        <Upload size={16} />
        Đăng tài liệu
      </button>
    );
  }

  return (
    <form className="document-upload-form" onSubmit={submit}>
      <div className="field">
        <label htmlFor="document-file">File PDF hoặc DOCX</label>
        <input
          id="document-file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={selectFile}
          type="file"
          required
        />
      </div>

      <div className="field">
        <label htmlFor="document-title">Tiêu đề</label>
        <input
          id="document-title"
          onChange={(event) => setTitle(event.target.value)}
          placeholder={file?.name || "Tên hiển thị của tài liệu"}
          value={title}
        />
      </div>

      <div className="field">
        <label htmlFor="document-description">Mô tả</label>
        <textarea
          id="document-description"
          onChange={(event) => setDescription(event.target.value)}
          value={description}
        />
      </div>

      <div className="field-row">
        <div className="field">
          <label htmlFor="document-visibility">Phạm vi xem</label>
          <select
            id="document-visibility"
            onChange={(event) =>
              setVisibility(event.target.value as DocumentItem["visibility"])
            }
            value={visibility}
          >
            <option value="ORGANIZATION">Toàn tổ chức</option>
            <option value="PRIVATE">Chỉ người đăng</option>
          </select>
        </div>

        {isSystemAdmin ? (
          <div className="field">
            <label htmlFor="document-organization">Tổ chức</label>
            <select
              id="document-organization"
              onChange={(event) => setOrganization(event.target.value)}
              value={organization}
              required
            >
              <option value="">Chọn tổ chức</option>
              {organizations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
        ) : null}
      </div>

      <div className="document-upload-actions">
        <button
          className="text-button"
          disabled={uploading}
          onClick={() => setIsOpen(false)}
          type="button"
        >
          Hủy
        </button>
        <button className="primary-button" disabled={uploading} type="submit">
          <Upload size={16} />
          {uploading ? "Đang đăng" : "Đăng tài liệu"}
        </button>
      </div>
    </form>
  );
}
