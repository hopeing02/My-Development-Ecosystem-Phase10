package dev.mde.autoknowledge;

final class KnowledgeDocumentCandidate {
    final String id;
    final String title;
    final String relativePath;

    KnowledgeDocumentCandidate(String id, String title, String relativePath) {
        this.id = id;
        this.title = title;
        this.relativePath = relativePath;
    }

    String label() {
        return title + "\n" + relativePath;
    }
}
