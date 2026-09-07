import re
from pathlib import Path
import pymupdf  # PyMuPDF

PDF_PATH = Path("ai act regulation eu 20241689-QT0125001ENN.pdf")
OUTPUT_DIR = Path("week5/knowledge-base")

ARTICLES_DIR = OUTPUT_DIR / "articles"
RECITALS_DIR = OUTPUT_DIR / "recitals"
ANNEXES_DIR = OUTPUT_DIR / "annexes"

for folder in [ARTICLES_DIR, RECITALS_DIR, ANNEXES_DIR]:
    folder.mkdir(parents = True, exist_ok = True)


# --------------------------------------------------
# 1. Extract all text from the PDF
# --------------------------------------------------

doc = pymupdf.open(PDF_PATH)

pages = []

# Skip the front matter / table of contents.
# PyMuPDF uses zero-based page numbering.
START_PAGE = 11

for page_number in range(START_PAGE, len(doc)):
    page = doc[page_number]
    text = page.get_text("text")
    pages.append(text)

full_text = "\n".join(pages)

# Stop Article parsing before the Annexes
annex_start = re.search(r"(?m)^ANNEX I\s*$", full_text)

if annex_start:
    article_text_source = full_text[:annex_start.start()]
else:
    article_text_source = full_text

print(f"Pages: {len(doc)}")
print(f"Characters extracted: {len(full_text):,}")

# --------------------------------------------------
# 2. Clean PDF extraction artifacts
# --------------------------------------------------

def clean_pdf_text(text: str) -> str:
    # Remove standalone PDF page numbers
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

# --------------------------------------------------
# 3. Extract Articles
# --------------------------------------------------

article_pattern = re.compile(
    r"(?m)^Article\s+(\d+)\s*$"
)

article_matches = list(article_pattern.finditer(article_text_source))

print(f"Found {len(article_matches)} article headings")


# Create Article Markdown files
for i, match in enumerate(article_matches):
    article_number = int(match.group(1))

    start = match.start()

    if i + 1 < len(article_matches):
        end = article_matches[i + 1].start()
    else:
        end = len(article_text_source)

    article_text = article_text_source[start:end].strip()

    # Remove PDF artifacts such as page numbers
    article_text = clean_pdf_text(article_text)
    
    output_file = ARTICLES_DIR / f"article_{article_number:03d}.md"

    markdown = f"""# Article {article_number}

## Source

Regulation (EU) 2024/1689 - Artificial Intelligence Act

## Official text

{article_text}
"""

    output_file.write_text(
        markdown,
        encoding = "utf-8"
    )

print("Article files created.")


# --------------------------------------------------
# 4. Extract Recitals
# --------------------------------------------------

# The recitals begin after "Whereas:"
# and end before "HAVE ADOPTED THIS REGULATION:"
recitals_start = re.search(
    r"Whereas\s*:",
    full_text,
    re.IGNORECASE
)

recitals_end = re.search(
    r"HAVE ADOPTED THIS REGULATION\s*:",
    full_text,
    re.IGNORECASE
)

if recitals_start and recitals_end:
    recitals_text = full_text[
        recitals_start.end():recitals_end.start()
    ]
else:
    raise ValueError(
        "Could not identify the beginning or end of the recital section."
    )


# --------------------------------------------------
# Find all numbered markers
# --------------------------------------------------

# The PDF uses (1), (2), etc. both for genuine recitals
# and for footnotes. Therefore this first finds all candidates.
recital_pattern = re.compile(
    r"(?m)^\s*\((\d{1,3})\)\s*"
)

all_matches = list(
    recital_pattern.finditer(recitals_text)
)

print(f"Found {len(all_matches)} raw numbered matches")


# --------------------------------------------------
# Identify the genuine Recitals 1-180
# --------------------------------------------------

# Genuine recitals form the sequence:
# (1), (2), ..., (180)
#
# We work backwards from Recital 180.
# This avoids confusing footnote numbers with recital numbers.

recital_matches = []

current_position = len(recitals_text)

for expected_number in range(180, 0, -1):

    candidates = [
        match
        for match in all_matches
        if int(match.group(1)) == expected_number
        and match.start() < current_position
    ]

    if not candidates:
        raise ValueError(
            f"Could not find Recital {expected_number}"
        )

    # Select the last occurrence before the next genuine recital
    chosen_match = max(
        candidates,
        key=lambda match: match.start()
    )

    recital_matches.append(chosen_match)

    current_position = chosen_match.start()


# We found them backwards, so restore 1 -> 180 order
recital_matches.reverse()


# --------------------------------------------------
# Validate the result
# --------------------------------------------------

recital_numbers = [
    int(match.group(1))
    for match in recital_matches
]

print(f"Found {len(recital_matches)} genuine recitals")
print("First recital numbers:", recital_numbers[:10])
print("Last recital numbers:", recital_numbers[-10:])


# --------------------------------------------------
# Create one Markdown file per recital
# --------------------------------------------------

for i, match in enumerate(recital_matches):
    recital_number = int(match.group(1))

    start = match.start()

    if i + 1 < len(recital_matches):
        end = recital_matches[i + 1].start()
    else:
        end = len(recitals_text)

    recital_text = recitals_text[start:end].strip()

    # Remove PDF artifacts such as standalone page numbers
    recital_text = clean_pdf_text(recital_text)

    output_file = (
        RECITALS_DIR /
        f"recital_{recital_number:03d}.md"
    )

    markdown = f"""# Recital {recital_number}

## Source

Regulation (EU) 2024/1689 - Artificial Intelligence Act

## Official text

{recital_text}
"""

    output_file.write_text(
        markdown,
        encoding = "utf-8"
    )

print("Recital files created.")


# --------------------------------------------------
# 5. Extract Annexes
# --------------------------------------------------

# The annex section begins at ANNEX I
annex_start = re.search(
    r"(?m)^ANNEX I\s*$",
    full_text
)

if not annex_start:
    raise ValueError("Could not find ANNEX I")

annex_text_source = full_text[annex_start.start():]

# Match standalone annex headings such as:
# ANNEX I
# ANNEX II
# ANNEX III
annex_pattern = re.compile(
    r"(?m)^ANNEX\s+([IVXLCDM]+)\s*$"
)

annex_matches = list(
    annex_pattern.finditer(annex_text_source)
)

print(f"Found {len(annex_matches)} annexes")

annex_numbers = [
    match.group(1)
    for match in annex_matches
]

print("Annexes found:", annex_numbers)


# --------------------------------------------------
# Create one Markdown file per annex
# --------------------------------------------------

for i, match in enumerate(annex_matches):
    annex_number = match.group(1)

    start = match.start()

    if i + 1 < len(annex_matches):
        end = annex_matches[i + 1].start()
    else:
        end = len(annex_text_source)

    annex_text = annex_text_source[start:end].strip()

    annex_text = clean_pdf_text(annex_text)

    output_file = (
        ANNEXES_DIR /
        f"annex_{annex_number}.md"
    )

    markdown = f"""# Annex {annex_number}

## Source

Regulation (EU) 2024/1689 - Artificial Intelligence Act

## Official text

{annex_text}
"""

    output_file.write_text(
        markdown,
        encoding = "utf-8"
    )

print("Annex files created.")
