"""Print the seeded knowledge base from Supabase, one section at a time.

This is the "send" side of the knowledge base: it reads the rows back from the
database through the same functions the AI agent uses (db.list_sections and
db.get_section), so you can verify the seed worked without running the pipeline.
"""

from app import db

for section in db.list_sections():
    print(f"\n===== {section} =====")
    for entry in db.get_section(section):
        print(f"\n## {entry['title']}\n{entry['content']}")
