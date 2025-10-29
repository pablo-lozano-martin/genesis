# Orbio Knowledge Base

This directory contains company information used by the Orbio onboarding chatbot to answer employee questions about policies, benefits, starter kits, office locations, IT setup, and company culture.

## Current Documents

The knowledge base includes the following Orbio company documents:

1. **benefits_and_perks.md** - Comprehensive employee benefits information
   - Health insurance (medical, dental, vision)
   - 401(k) retirement plan
   - PTO and leave policies
   - Professional development budget
   - Wellness benefits and gym membership
   - Employee discounts and perks

2. **starter_kit_options.md** - Hardware and equipment choices for new hires
   - Mouse options (Logitech MX Master 3 vs. basic wireless)
   - Keyboard options (mechanical vs. standard wireless)
   - Bag options (backpack vs. messenger bag)
   - Detailed pros/cons for each option

3. **office_locations.md** - Office location and access information
   - San Francisco HQ address and directions
   - Parking information and costs
   - Public transportation options
   - Building access and badge information
   - Nearby amenities

4. **it_setup_guide.md** - Technology setup instructions
   - Laptop configuration and security
   - Email and Slack setup
   - VPN access (GlobalProtect)
   - Password manager (1Password)
   - Multi-factor authentication
   - Software installation requests

5. **onboarding_schedule.md** - First day and first 90 days timeline
   - First day detailed schedule
   - Week 1 overview
   - Monthly milestones
   - Onboarding checklist
   - Training requirements

6. **company_culture.md** - Culture, values, and workplace norms
   - Core values (Customer Obsession, Ownership, Learning, Bias for Action, Collaboration)
   - Work environment (hybrid, dress code, hours)
   - Communication norms (Slack, email, meetings)
   - Diversity, equity, and inclusion
   - Work-life balance and professional growth

## Supported Formats
- `.txt` - Plain text files
- `.md` - Markdown files (recommended for rich formatting)
- `.pdf` - PDF documents (parser not yet implemented)

## Ingestion

To ingest documents into ChromaDB, run from the backend directory:

```bash
# Via Docker (recommended)
docker-compose exec backend python scripts/ingest_documents.py knowledge_base/

# Or locally (requires environment setup)
python scripts/ingest_documents.py knowledge_base/
```

The script will:
1. Scan for supported file types (`.txt`, `.md`)
2. Chunk documents into 512-word segments with 50-word overlap
3. Generate embeddings using ChromaDB's default model
4. Store in the `genesis_documents` collection

## Testing RAG Search

To test that documents are properly indexed and retrievable:

```bash
# Run manual test script
docker-compose exec backend python test_orbio_rag.py
```

Expected results:
- Queries about starter kits → Returns `starter_kit_options.md`
- Queries about benefits → Returns `benefits_and_perks.md`
- Queries about office location → Returns `office_locations.md`
- Queries about IT setup → Returns `it_setup_guide.md`
- Queries about dress code → Returns `company_culture.md`
- Queries about first day → Returns `onboarding_schedule.md`

All similarity scores should be >0.5, with most >0.6 for relevant queries.

## Document Guidelines

### Writing Style
- Use clear, conversational language (chatbot will surface this content)
- Keep sentences concise and scannable
- Use bullet points and lists for easy reading
- Include specific details (not generic placeholder text)

### Document Structure
- Start with a brief introduction (1-2 sentences)
- Use markdown headers (##, ###) for sections
- Keep documents focused on one topic (500-2000 words)
- Target ~512 words per logical section (aligns with chunk size)

### Updating Documents
1. Edit the markdown file in this directory
2. Clear ChromaDB collection: `rm -rf backend/chroma_db/`
3. Re-run ingestion script
4. Test with sample queries to verify changes

## RAG Configuration

The RAG system uses these settings (defined in `.env`):

- **Collection Name**: `CHROMA_COLLECTION_NAME=genesis_documents`
- **Chunk Size**: `RETRIEVAL_CHUNK_SIZE=512` (words)
- **Chunk Overlap**: `RETRIEVAL_CHUNK_OVERLAP=50` (words)
- **Top-K Results**: `RETRIEVAL_TOP_K=5` (documents returned per query)
- **Similarity Threshold**: `RETRIEVAL_SIMILARITY_THRESHOLD=0.5`

## Troubleshooting

**No results returned for queries:**
- Verify documents are ingested: Check for `chroma_db/` directory
- Re-run ingestion script
- Check logs for errors during ingestion

**Irrelevant results:**
- Review document content for clarity
- Ensure questions use similar language to documents
- Consider adjusting chunk size if context is being split awkwardly

**Ingestion errors:**
- Verify file encoding is UTF-8
- Check markdown syntax is valid
- Ensure file extensions are `.txt` or `.md`

## Sample Queries

Test the knowledge base with these example queries:

- "What starter kit options are available?"
- "What are the employee benefits?"
- "Where is the office located?"
- "How do I set up my laptop for IT?"
- "What is the dress code?"
- "What should I expect on my first day?"
- "How do I park at the office?"
- "What's the 401k match?"
- "Do I get a gym membership?"
- "What's the remote work policy?"
