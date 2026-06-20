import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_csv('analysis/hard_examples.csv')
print('Total rows:', len(df))
wrong = df[df['correct'] == False]
print('Incorrect:', len(wrong))

print('\nMistakes by true_label:')
print(wrong['true_label'].value_counts().to_string())

print('\nMistakes by predicted_label:')
print(wrong['predicted_label'].value_counts().to_string())

print('\nTop 20 highest-confidence mistakes:')
top20 = wrong.nlargest(20, 'confidence')
for _, row in top20.iterrows():
    text = str(row['text'])[:70].encode('ascii', 'replace').decode('ascii')
    print(f"  True={row['true_label']:16s} Pred={row['predicted_label']:16s} Conf={row['confidence']:.4f} Lang={row['language']:10s} Text={text}")
