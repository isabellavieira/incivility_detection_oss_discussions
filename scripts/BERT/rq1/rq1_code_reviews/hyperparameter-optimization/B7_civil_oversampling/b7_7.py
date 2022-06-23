# -*- coding: utf-8 -*-
"""civil_py_script2

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1gpUyPAvnuKZTJtJoSKHeLqzz51XBfOFZ

## Code for civil/uncivil classification. 
This contains the implementation of EDA, random oversampling, and bayesian optimization with Optuna.

Installations
"""

# ! pip install transformers
# ! pip install datasets
# ! pip install scikit-learn
# ! pip install nltk
# ! pip install imbalanced-learn
# ! pip install optuna

# import transformers
# print(transformers.__version__)

# import datasets
# print(datasets.__version__)

# import sklearn
# print(sklearn.__version__)

# import nltk
# print(nltk.__version__)

# import imblearn
# print(imblearn.__version__)

# import optuna
# print(optuna.__version__)

# set model as required (a whole list of possible pre-trained Transformer models here: https://huggingface.co/transformers/pretrained_models.html)
model_checkpoint = "bert-base-uncased"
batch_size = 16

# required to use the inbuilt Transformers Trainer class
from datasets import load_dataset, load_metric

# set metric as required. Available inbuilt metrics (extend the datasets Metric class) are here: https://github.com/huggingface/datasets/tree/master/metrics. Can write your own custom metric too. 
metric = load_metric('matthews_correlation')

# uncomment the below to print selected metric details
# print(metric)

"""### Get data"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# read CSVs
url_c = 'https://github.com/ahlraf/datasets/raw/main/utf_civil.csv'
url_uc = 'https://github.com/ahlraf/datasets/raw/main/utf_uncivil.csv'

# getting datasets
df_c = pd.read_csv(url_c, header='infer', skip_blank_lines=True, encoding="utf-8")
df_uc = pd.read_csv(url_uc, header='infer', skip_blank_lines=True, encoding="utf-8")

df_c.dropna(axis=0,how="any",inplace=True)
df_uc.dropna(axis=0,how="any",inplace=True)

d1 = pd.DataFrame(['civil' for _ in range(df_c.shape[0])], columns=['label'])
df_civ = pd.concat([df_c['quotation'], d1], axis=1)

d2 = pd.DataFrame(['uncivil' for _ in range(df_uc.shape[0])], columns=['label'])
df_unciv = pd.concat([df_uc['quotation'], d2], axis=1)

df = pd.concat([df_civ, df_unciv], ignore_index=True)

print("Original count:", df['label'].value_counts(normalize=False))

# set numeric values
df['label'] = [0 if x=='civil' else 1 for x in df['label']]

print("\n\nOriginal dataframe\n")
print(df.head())

"""<br>Split (stratified along label) into train, eval, test sets. Ratio here: 70:15:15."""

train, temp = train_test_split(df, random_state=2018, test_size=0.3, stratify=df['label'])
eval, test = train_test_split(temp, random_state=2018, test_size=0.5, stratify=temp['label'])

train = train.reset_index(drop=True)
eval = eval.reset_index(drop=True) 
test = test.reset_index(drop=True)

print("Train count:", train['label'].value_counts(normalize=False))

"""### EDA implementation"""

# imports for EDA
import random
from random import shuffle
random.seed(1)

import re

import nltk
nltk.download("wordnet")
from nltk.corpus import wordnet

#stop words list
stop_words = ['i', 'me', 'my', 'myself', 'we', 'our', 
			'ours', 'ourselves', 'you', 'your', 'yours', 
			'yourself', 'yourselves', 'he', 'him', 'his', 
			'himself', 'she', 'her', 'hers', 'herself', 
			'it', 'its', 'itself', 'they', 'them', 'their', 
			'theirs', 'themselves', 'what', 'which', 'who', 
			'whom', 'this', 'that', 'these', 'those', 'am', 
			'is', 'are', 'was', 'were', 'be', 'been', 'being', 
			'have', 'has', 'had', 'having', 'do', 'does', 'did',
			'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
			'because', 'as', 'until', 'while', 'of', 'at', 
			'by', 'for', 'with', 'about', 'against', 'between',
			'into', 'through', 'during', 'before', 'after', 
			'above', 'below', 'to', 'from', 'up', 'down', 'in',
			'out', 'on', 'off', 'over', 'under', 'again', 
			'further', 'then', 'once', 'here', 'there', 'when', 
			'where', 'why', 'how', 'all', 'any', 'both', 'each', 
			'few', 'more', 'most', 'other', 'some', 'such', 'no', 
			'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 
			'very', 's', 't', 'can', 'will', 'just', 'don', 
			'should', 'now', '']

#cleaning up text
import re
def get_only_chars(line):

  clean_line = ""

  # change this as required!

  # line = line.replace("’", "")
  # line = line.replace("'", "")
  line = line.replace("-", " ") #replace hyphens with spaces
  line = line.replace("\t", " ")
  line = line.replace("\n", " ")
  # line = line.lower()

  for char in line:
    # can set own range as required.
    if char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.?!.;:\'\" ':
      clean_line += char
    else:
      clean_line += ' '

  clean_line = re.sub(' +',' ',clean_line) #delete extra spaces
  if clean_line[0] == ' ':
    clean_line = clean_line[1:]
  return clean_line

########################################################################
# Synonym replacement
# Replace n words in the sentence with synonyms from wordnet
########################################################################


def synonym_replacement(words, n):
	new_words = words.copy()
	random_word_list = list(set([word for word in words if word not in stop_words]))
	random.shuffle(random_word_list)
	num_replaced = 0
	for random_word in random_word_list:
		synonyms = get_synonyms(random_word)
		if len(synonyms) >= 1:
			synonym = random.choice(list(synonyms))
			new_words = [synonym if word == random_word else word for word in new_words]
			#print("replaced", random_word, "with", synonym)
			num_replaced += 1
		if num_replaced >= n: #only replace up to n words
			break

	sentence = ' '.join(new_words)
	new_words = sentence.split(' ')

	return new_words

def get_synonyms(word):
	synonyms = set()
	for syn in wordnet.synsets(word): 
		for l in syn.lemmas(): 
			synonym = l.name().replace("_", " ").replace("-", " ").lower()
			synonym = "".join([char for char in synonym if char in ' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'])
			synonyms.add(synonym) 
	if word in synonyms:
		synonyms.remove(word)
	return list(synonyms)

########################################################################
# Random deletion
# Randomly delete words from the sentence with probability p
########################################################################

def random_deletion(words, p):

	#obviously, if there's only one word, don't delete it
	if len(words) == 1:
		return words

	#randomly delete words with probability p
	new_words = []
	for word in words:
		r = random.uniform(0, 1)
		if r > p:
			new_words.append(word)

	#if you end up deleting all words, just return a random word
	if len(new_words) == 0:
		rand_int = random.randint(0, len(words)-1)
		return [words[rand_int]]

	return new_words

########################################################################
# Random swap
# Randomly swap two words in the sentence n times
########################################################################

def random_swap(words, n):
	new_words = words.copy()
	for _ in range(n):
		new_words = swap_word(new_words)
	return new_words

def swap_word(new_words):
	random_idx_1 = random.randint(0, len(new_words)-1)
	random_idx_2 = random_idx_1
	counter = 0
	while random_idx_2 == random_idx_1:
		random_idx_2 = random.randint(0, len(new_words)-1)
		counter += 1
		if counter > 3:
			return new_words
	new_words[random_idx_1], new_words[random_idx_2] = new_words[random_idx_2], new_words[random_idx_1] 
	return new_words

########################################################################
# Random insertion
# Randomly insert n words into the sentence
########################################################################

def random_insertion(words, n):
	new_words = words.copy()
	for _ in range(n):
		add_word(new_words)
	return new_words

def add_word(new_words):
	synonyms = []
	counter = 0
	while len(synonyms) < 1:
		random_word = new_words[random.randint(0, len(new_words)-1)]
		synonyms = get_synonyms(random_word)
		counter += 1
		if counter >= 10:
			return
	random_synonym = synonyms[0]
	random_idx = random.randint(0, len(new_words)-1)
	new_words.insert(random_idx, random_synonym)

########################################################################
# main data augmentation function
########################################################################

def eda(sentence, alpha_sr=0.1, alpha_ri=0.1, alpha_rs=0.1, p_rd=0.1, num_aug=9):
	
	sentence = get_only_chars(sentence)
	words = sentence.split(' ')
	words = [word for word in words if word is not '']
	num_words = len(words)
	
	augmented_sentences = []
	num_new_per_technique = int(num_aug/4)+1

	#sr
	if (alpha_sr > 0):
		n_sr = max(1, int(alpha_sr*num_words))
		for _ in range(num_new_per_technique):
			a_words = synonym_replacement(words, n_sr)
			augmented_sentences.append(' '.join(a_words))

	#ri
	if (alpha_ri > 0):
		n_ri = max(1, int(alpha_ri*num_words))
		for _ in range(num_new_per_technique):
			a_words = random_insertion(words, n_ri)
			augmented_sentences.append(' '.join(a_words))

	#rs
	if (alpha_rs > 0):
		n_rs = max(1, int(alpha_rs*num_words))
		for _ in range(num_new_per_technique):
			a_words = random_swap(words, n_rs)
			augmented_sentences.append(' '.join(a_words))

	#rd
	if (p_rd > 0):
		for _ in range(num_new_per_technique):
			a_words = random_deletion(words, p_rd)
			augmented_sentences.append(' '.join(a_words))

	augmented_sentences = [get_only_chars(sentence) for sentence in augmented_sentences]
	shuffle(augmented_sentences)

	#trim so that we have the desired number of augmented sentences
	if num_aug >= 1:
		augmented_sentences = augmented_sentences[:num_aug]
	else:
		keep_prob = num_aug / len(augmented_sentences)
		augmented_sentences = [s for s in augmented_sentences if random.uniform(0, 1) < keep_prob]

	#append the original sentence
	augmented_sentences.append(sentence)

	return augmented_sentences

"""EDA sentence generator wrapper"""

def gen_eda(orig_train_df, output_train_df, alpha_sr, alpha_ri, alpha_rs, alpha_rd, num_aug=9):

  """
  Parameters: 
  orig_train_df: unaugmented train (pandas) DataFrame
  output_train_df: empty DataFrame
  alpha_sr = augmentation parameter for synonym replacement
  alpha_ri = augmentation parameter for random insertion
  alpha_rs = augmentation parameter for random swapping
  alpha_rd = augmentation parameter for random deletion
  num_aug = number of generated sentences per input sentence.
  (generates (int(num_aug/4) + 1) sentences per task, shuffles dataset and trims to num_aug generated per sentence.)

  Returns: 
  output_train_df = pandas DataFrame containing sentences from the original DataFrame + newly generated sentences.
  Size of output_train_df = (size of orig_train_df)*(num_aug + 1)
  """
  for idx in orig_train_df.index:
    label = orig_train_df.loc[idx, 'label']
    sentence = orig_train_df.loc[idx, 'quotation']
    aug_sentences = eda(sentence, alpha_sr=alpha_sr, alpha_ri=alpha_ri, alpha_rs=alpha_rs, p_rd=alpha_rd, num_aug=num_aug)
    d = {}
    d["quotation"] = aug_sentences
    d["label"] = [label for _ in range(len(aug_sentences))]
    df = pd.DataFrame(d)
    output_train_df = pd.concat([output_train_df, df], ignore_index=True)
  
  print("Generated", num_aug, "sentences per input sentence with EDA")
  return output_train_df

# empty DataFrame
output_train = pd.DataFrame(columns=["quotation", "label"])
output_train

"""**Recommended EDA hyperparameters here:**<br>(configurations for grid search)

```
alpha_sr in {0.05, 0.2}
alpha_ri in {0.05, 0.1}
alpha_rs in {0.05}
alpha_rd in {0.05}
num_aug in {8, 16}
```


"""

# augmented train DataFrame
aug_train = gen_eda(train, output_train, 0.05, 0.05, 0.05, 0.05, 8)

# print("\n\nAugmented train dataframe\n")
# print(aug_train.head())

print("\n\n# of datapoints before augmentation:", len(train))
print("# of datapoints after augmentation:", len(aug_train))

"""### Class balancing: random oversampling"""

from imblearn.over_sampling import RandomOverSampler
## for random undersampling, uncomment the below:
## from imblearn.under_sampling import RandomUnderSampler
from collections import Counter

train_text = aug_train["quotation"]
train_labels = aug_train["label"]
print("\n\nLabel count before oversampling:", Counter(train_labels))

X_train_np, y_train_l = train_text.to_numpy(), train_labels.to_list()
X_train_np = X_train_np.reshape((-1, 1))

# from sklearn.utils.multiclass import type_of_target - need this!
# print(type_of_target(tr_list))

ros = RandomOverSampler(sampling_strategy="minority")
X_resampled, y_resampled = ros.fit_resample(X_train_np, y_train_l)

# for random undersampling, uncomment the below:
# rus = RandomUnderSampler(sampling_strategy="majority")
# X_resampled, y_resampled = rus.fit_resample(X_train_np, y_train_np)

shape = (len(y_resampled),)
X_resampled = X_resampled.reshape(shape)

train_text = X_resampled
train_labels = y_resampled

print("Label count after oversampling:", Counter(train_labels))
# print("Label count after undersampling:", Counter(train_labels))

train = pd.DataFrame({'quotation': train_text, 'label': train_labels})

print("\n\nTrain dataset after augmentation and oversampling\n")
print(train.head())

# convert to dataset for easier Transformer integration
from datasets import Dataset

train_ds = Dataset.from_pandas(train)
eval_ds = Dataset.from_pandas(eval)
test_ds = Dataset.from_pandas(test)

# train_ds[0]

print("\n\nMetric details")
print(metric)

from transformers import AutoTokenizer
    
tokenizer = AutoTokenizer.from_pretrained(model_checkpoint, use_fast=True)

# uncomment below to test
# tokenizer("Hello, this one sentence!", "And this sentence goes with it.")

def tokenize_function(ds):
  return tokenizer(ds["quotation"], truncation=True)

# uncomment below to test
# tokenize_function(train_ds[:5])

# tokenize datasets (preprocessing)
encoded_train_ds = train_ds.map(tokenize_function, batched=True)
encoded_eval_ds = eval_ds.map(tokenize_function, batched=True)
encoded_test_ds = test_ds.map(tokenize_function, batched=True)

print("\n\nEncoded train dataset sample\n")
print(encoded_train_ds[0])

"""### Fine tuning model"""

from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer

num_labels = 2
model = AutoModelForSequenceClassification.from_pretrained(model_checkpoint, num_labels=num_labels)

metric_name = "matthews_correlation"

# define TrainingArguments: arguments/ hyperparameters used in training/eval loop. You can find a complete list here: https://huggingface.co/transformers/main_classes/trainer.html#transformers.TrainingArguments.
# Most of these can be optimized
args = TrainingArguments(
    "exp-b7",
    evaluation_strategy = "epoch",
    save_strategy = "epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=batch_size,
    per_device_eval_batch_size=batch_size,
    num_train_epochs=1,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model=metric_name
)

# needed during the training/eval loop (Trainer class instance). If you pass in compute_metrics=None (the default), evaluation is done with prediction loss only (no metric optimization objective)
def compute_metrics(eval_pred):
  predictions, labels = eval_pred
  predictions = np.argmax(predictions, axis=1)
  return metric.compute(predictions=predictions, references=labels)

####### Uncomment the below to train/evaluate the model without hyperparameter optimization

# trainer = Trainer(
#     model,
#     args,
#     train_dataset=encoded_train_ds,
#     eval_dataset=encoded_eval_ds,
#     tokenizer=tokenizer,
#     compute_metrics=compute_metrics
# )

# trainer.train()
# trainer.evaluate()

"""### Hyperparameter search"""

# uncomment the below to create a Dataset that includes only 1/num_shards of this dataset. useful for running distributed training, as it allows each worker to read a unique subset. 
# if we do have distributed training, should shard much earlier (pre-EDA etc.) to optimize work distribution.


# train_ds_hyp = encoded_train_ds.shard(index=1, num_shards=25)
# eval_ds_hyp = encoded_eval_ds.shard(index=1, num_shards=10)

def model_init():
    return AutoModelForSequenceClassification.from_pretrained(model_checkpoint, num_labels=num_labels)

# Trainer is a simple, feature-complete training and eval loop for PyTorch, optimized for Hugging Face Transformers. https://huggingface.co/transformers/main_classes/trainer.html#transformers.Trainer
trainer = Trainer(
    model_init=model_init,
    args=args,
    train_dataset=encoded_train_ds,
    eval_dataset=encoded_eval_ds,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics
)

"""By default, optuna optimizes the metric over: 


```
"learning_rate": trial.suggest_float("learning_rate", 1e-6, 1e-4, log=True),
"num_train_epochs": trial.suggest_int("num_train_epochs", 1, 5),
"seed": trial.suggest_int("seed", 1, 40),
"per_device_train_batch_size": trial.suggest_categorical("per_device_train_batch_size", [4, 8, 16, 32, 64])
```

Customize a search space function, choosing suitable hyperparameters from the TrainingArguments list.


"""

def hp_space_optuna(trial):
  return {
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "num_train_epochs": trial.suggest_int("num_train_epochs", 2, 10),
        "per_device_train_batch_size": trial.suggest_categorical("per_device_train_batch_size", [4, 8, 16]),
        "weight_decay": trial.suggest_float("weight_decay", 0.01, 0.3, log=True),
        "warmup_steps": trial.suggest_int("warmup_steps", 0, 500)
    }

"""Launch an hyperparameter search using optuna. The optimized quantity is determined by compute_objective, which defaults to a function returning the evaluation loss when no metric is provided, the sum of all metrics otherwise. To use this, we must have a model_init() in the Trainer, as the model is reinitialized in each run. 

By default, n_trials=100, direction="minimize".

We don't need to define our own compute_objective function. The metric we specified in the Trainer instance is used as the optimization quantity. If no metric is provided, evaluation loss is used. If multiple metrics are provided, it uses the sum of all metrics.
"""

best_run = trainer.hyperparameter_search(hp_space_optuna, n_trials=50, direction="maximize")
# best_run = trainer.hyperparameter_search(n_trials=3, direction="maximize")

# print details of best run (prints best run ID, maximized metric, and a dictionary of optimized hyperparameters)
print(best_run)