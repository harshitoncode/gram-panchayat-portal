import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def preprocess_text(text):
    """Lowercase, remove special characters, normalize whitespace."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def find_duplicates(new_complaint, existing_complaints, threshold=0.3,
                    category_boost=0.15, ward_boost=0.10, max_results=5):
    """Find potential duplicate complaints using TF-IDF cosine similarity
    with category and ward boosting."""
    if not existing_complaints:
        return []

    # Combine title + description for each existing complaint
    existing_texts = [
        preprocess_text(c['title'] + ' ' + c['description'])
        for c in existing_complaints
    ]

    # Combine title + description for the new complaint
    new_text = preprocess_text(
        new_complaint['title'] + ' ' + new_complaint['description']
    )

    # Vectorize all texts together (existing + new as last)
    all_texts = existing_texts + [new_text]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Cosine similarity of new (last row) vs all existing
    new_vector = tfidf_matrix[-1]
    existing_vectors = tfidf_matrix[:-1]
    similarities = cosine_similarity(new_vector, existing_vectors)[0]

    # Calculate adjusted scores with category and ward boosting
    results = []
    for i, complaint in enumerate(existing_complaints):
        base_score = float(similarities[i])
        adjusted_score = base_score

        if complaint.get('category') == new_complaint.get('category'):
            adjusted_score += category_boost

        if complaint.get('ward') == new_complaint.get('ward'):
            adjusted_score += ward_boost

        # Cap at 1.0
        adjusted_score = min(adjusted_score, 1.0)

        if adjusted_score >= threshold:
            results.append({
                'complaint_id': complaint['id'],
                'complaint_uid': complaint['complaint_uid'],
                'similarity_score': round(adjusted_score, 4),
                'title': complaint['title'],
                'description': complaint['description'],
                'category': complaint['category'],
                'ward': complaint['ward'],
            })

    # Sort descending by adjusted_score and return top max_results
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    return results[:max_results]
