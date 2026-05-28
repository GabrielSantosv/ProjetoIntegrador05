-- Schema inicial para o novo banco de dados do Projeto Integrador
-- Alvo: PostgreSQL

CREATE TABLE IF NOT EXISTS auth_user (
    id integer PRIMARY KEY,
    username varchar(150) NOT NULL,
    email varchar(254) DEFAULT ''
);

INSERT INTO auth_user (id, username, email)
VALUES (1, 'demo', 'demo@example.com')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS folders (
    id varchar(64) PRIMARY KEY,
    owner_id integer REFERENCES auth_user(id),
    name varchar(255) NOT NULL,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL
);

CREATE TABLE IF NOT EXISTS documents_document (
    id bigserial PRIMARY KEY,
    owner_id integer REFERENCES auth_user(id),
    title varchar(255) NOT NULL,
    file varchar(500) NOT NULL,
    status varchar(50) NOT NULL,
    document_type varchar(100),
    extracted_text text,
    extracted_data jsonb DEFAULT '{}'::jsonb,
    entities jsonb DEFAULT '[]'::jsonb,
    legal_opinion text,
    risk_score numeric DEFAULT 0,
    error_message text,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    folder_id varchar(64) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS rg_documents (
    id bigserial PRIMARY KEY,
    owner_id integer REFERENCES auth_user(id),
    original_filename varchar(500) NOT NULL,
    image_path varchar(500) NOT NULL,
    status varchar(50) NOT NULL DEFAULT 'processing',
    ocr_method varchar(50) DEFAULT '',
    nome text DEFAULT '',
    rg varchar(30) DEFAULT '',
    cpf varchar(20) DEFAULT '',
    data_nascimento varchar(20) DEFAULT '',
    municipio text DEFAULT '',
    nome_mae text DEFAULT '',
    nome_pai text DEFAULT '',
    raw_text text DEFAULT '',
    error_message text DEFAULT '',
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    image_path_verso varchar(500) DEFAULT '',
    lado_detectado varchar(20) DEFAULT '',
    folder_id varchar(64) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS process_documents (
    id bigserial PRIMARY KEY,
    owner_id integer REFERENCES auth_user(id),
    folder_id varchar(64) NOT NULL DEFAULT '',
    process_number varchar(80) NOT NULL,
    source_document_id bigint,
    original_filename varchar(500) NOT NULL,
    file_path varchar(500) NOT NULL,
    status varchar(50) NOT NULL DEFAULT 'processing',
    extraction_method varchar(80) DEFAULT '',
    extracted_text text DEFAULT '',
    analysis_data jsonb DEFAULT '{}'::jsonb,
    summary text DEFAULT '',
    error_message text DEFAULT '',
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_folder_id
    ON documents_document(folder_id);

CREATE INDEX IF NOT EXISTS idx_documents_owner_id
    ON documents_document(owner_id);

CREATE INDEX IF NOT EXISTS idx_rg_documents_folder_id
    ON rg_documents(folder_id);

CREATE INDEX IF NOT EXISTS idx_rg_documents_owner_id
    ON rg_documents(owner_id);

CREATE INDEX IF NOT EXISTS idx_process_documents_folder_process
    ON process_documents(folder_id, process_number);

CREATE INDEX IF NOT EXISTS idx_process_documents_owner_id
    ON process_documents(owner_id);

CREATE INDEX IF NOT EXISTS idx_process_documents_source_document_id
    ON process_documents(source_document_id);
