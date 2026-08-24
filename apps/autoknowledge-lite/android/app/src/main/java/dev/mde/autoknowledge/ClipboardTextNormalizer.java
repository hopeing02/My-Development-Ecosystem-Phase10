package dev.mde.autoknowledge;

import java.util.ArrayList;
import java.util.List;

final class ClipboardTextNormalizer {
    String normalize(CharSequence value) {
        if (value == null) {
            return "";
        }
        String input = value.toString().replace("\r\n", "\n").replace('\r', '\n').trim();
        if (input.isEmpty()) {
            return "";
        }
        String[] lines = input.split("\n", -1);
        List<String> output = new ArrayList<>();
        boolean inCodeBlock = false;
        int emptyLines = 0;
        for (String line : lines) {
            String processed = inCodeBlock ? line : line.replaceFirst("[ \\t]+$", "");
            if (processed.trim().startsWith("```")) {
                inCodeBlock = !inCodeBlock;
            }
            if (!inCodeBlock && processed.isEmpty()) {
                emptyLines++;
                if (emptyLines > 2) {
                    continue;
                }
            } else {
                emptyLines = 0;
            }
            output.add(processed);
        }
        while (!output.isEmpty() && output.get(output.size() - 1).isEmpty()) {
            output.remove(output.size() - 1);
        }
        return String.join("\n", output);
    }
}
