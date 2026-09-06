# Tài Liệu Tham Khảo

Danh sách dưới đây ưu tiên bài báo gốc và tài liệu chính thức của công nghệ
được dùng trong project.

## Nền Tảng Học Thuật

1. Patrick Lewis và cộng sự, “Retrieval-Augmented Generation for
   Knowledge-Intensive NLP Tasks”, NeurIPS 2020.
   <https://papers.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html>
2. Nils Reimers và Iryna Gurevych, “Sentence-BERT: Sentence Embeddings using
   Siamese BERT-Networks”, EMNLP-IJCNLP 2019.
   <https://aclanthology.org/D19-1410/>
3. David Ferraiolo và Richard Kuhn, “Role-Based Access Controls”, NIST, 1992.
   <https://csrc.nist.gov/pubs/conference/1992/10/13/rolebased-access-controls/final>
4. NIST, “A Revised Model for Role Based Access Control”, NIST IR 6192.
   <https://doi.org/10.6028/NIST.IR.6192>

## Tài Liệu Công Nghệ

5. LangChain, “Splitting recursively - Text splitter integration guide”.
   <https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter>
6. Sentence Transformers, “Semantic Search”.
   <https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html>
7. Model card `paraphrase-multilingual-MiniLM-L12-v2`.
   <https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2>
8. pgvector, tài liệu chính thức về vector similarity search cho PostgreSQL.
   <https://github.com/pgvector/pgvector>
9. PaddleOCR, “General OCR Pipeline Usage Tutorial”.
   <https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html>
10. Django REST framework, “Permissions”.
    <https://www.django-rest-framework.org/api-guide/permissions/>
11. Django, “Deployment checklist”.
    <https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/>
12. Simple JWT, tài liệu refresh token và blacklist.
    <https://django-rest-framework-simplejwt.readthedocs.io/en/latest/>

## Cách Dùng Trong Báo Cáo

- Tài liệu 1 dùng cho định nghĩa và kiến trúc RAG.
- Tài liệu 2, 6 và 7 dùng cho embedding đa ngôn ngữ và semantic search.
- Tài liệu 3, 4 và 10 dùng cho mô hình RBAC và lý do phải lọc queryset trước
  retrieval.
- Tài liệu 5 dùng để giải thích lựa chọn LangChain
  `RecursiveCharacterTextSplitter`.
- Tài liệu 8 dùng cho PostgreSQL/pgvector và cosine distance.
- Tài liệu 9 dùng cho pipeline OCR và giới hạn nhận dạng.
- Tài liệu 11, 12 dùng cho phần bảo mật triển khai và JWT.
