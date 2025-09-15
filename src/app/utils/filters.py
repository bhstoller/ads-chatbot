import re
from datetime import datetime

def filter_expired_deadlines(docs):
    today = datetime.today().date()
    filtered_docs = []
    for doc in docs:
        text = doc.page_content
        matches = re.findall(r'([A-Za-z]+ \d{1,2}, \d{4})', text)
        keep = True
        for m in matches:
            try:
                d = datetime.strptime(m, "%B %d, %Y").date()
                if d < today:
                    keep = False
            except:
                pass
        if keep:
            filtered_docs.append(doc)
    return filtered_docs
