import pandas as pd
import os
import numpy as np
from urllib.request import urlretrieve
import time
import random
import json
import urllib
from PIL import Image
from tqdm import tqdm
from collections import defaultdict
from functools import partial
from clip import CLIP
import pickle
from prompt import *#make_caption_prompt,make_review_prompt,make_training_dict
import argparse
import pickle
from tqdm import tqdm
import re
from language_models import LLM

def save_json(obj, json_path):
    with open(json_path, 'w') as f:
        json.dump(obj, f)  
        
def load_multiple_dict(dict_names):
    d_all = {}
    for dict_name in dict_names:
        with open(dict_name, 'rb') as f:
            d = pickle.load(f)
            d_all.update(d)
            
    return d_all

class DataPreprocessor:
    def __init__(self):
        self.text_image_df = pd.read_csv('/home/yamanishi/project/trip_recommend/data/jalan/spot/text_image_pairs.csv', names=['image_url', 'text', 'spot_name', 'ind'])
        self.image_save_dir = '/home/yamanishi/project/trip_recommend/data/jalan_image_with_caption'
        self.graph_dir = '/home/yamanishi/project/trip_recommend/data/jalan/graph/'
        self.experience_df = pd.read_csv('/home/yamanishi/project/airport/src/data/experience_light.csv')
        self.popular_spots = set(self.experience_df.sort_values('review_count', ascending=False)['spot_name'].values[3000:10000])
        
    def download_images(self, start_count=0, end_count=0):
        for i in range(start_count, len(self.text_image_df)):
            if i==end_count:break
            print(i)
            image_url, spot_name, ind = self.text_image_df.loc[i, 'image_url'], self.text_image_df.loc[i, 'spot_name'], self.text_image_df.loc[i, 'ind']
            spot_name = spot_name.replace('/', '')
            save_image_path = os.path.join(self.image_save_dir, f'{spot_name}_{ind}.jpg')
            if os.path.exists(save_image_path):continue
            try:
                urlretrieve(image_url, save_image_path)
            except TypeError:
                continue
            except urllib.error.HTTPError:
                continue
            sleep_time = random.uniform(1, 1.5)
            time.sleep(sleep_time)
            
    def retrieve_reviews(self):
        def get_id(image_path):
            id = image_path.split('/')[-1]
            id = id.split('.')[0]
            return id
        
        clip = CLIP()
        df = []
        df_review = pd.read_pickle('/home/yamanishi/project/trip_recommend/data/jalan/review/review_all_period_.pkl')
        df_retrieved = pd.read_csv('../data/retrieved_reviews.csv', names=['spot_name', 'image_path', 'nearest_review', 'nearest_review_original', 'ind'])
        spot_names = df_retrieved['spot_name'].values
        for spot_name in tqdm(self.text_image_df['spot_name'].unique()):
            if spot_name in spot_names:continue
            df_tmp = self.text_image_df[self.text_image_df['spot_name']==spot_name]
            spot_images = [os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg') for i in range(len(df_tmp))
                                                           if os.path.exists(os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg'))]
            if len(spot_images)==0:continue
            df_review_tmp = df_review[df_review['spot']==spot_name]
            spot_reviews = []
            original_reviews = {}
            for review in df_review_tmp['review']:
                review_split = review.split('。')
                for r in review_split:
                    original_reviews[r]=review
                spot_reviews+=review_split
                
            spot_images = random.sample(spot_images, min(50, len(spot_images)))
            spot_reviews = random.sample(spot_reviews, min(2000, len(spot_reviews)))
            if len(spot_reviews)==0:continue
            retrieved_reviews = clip.retrieve_text_from_image(spot_images, spot_reviews)
            retrieved_original_reviews = [original_reviews[r] for r in retrieved_reviews]
            df = pd.DataFrame({'spot_name': spot_name, 'image_path': spot_images, 'nearest_review': retrieved_reviews,
                                    'nearest_review_original': retrieved_original_reviews})
            print(pd.DataFrame({'spot_name': spot_name, 'image_path': spot_images, 'nearest_review': retrieved_reviews,
                                    'nearest_review_original': retrieved_original_reviews}))
            df['id'] = df['image_path'].apply(get_id)
            df.to_csv('../data/retrieved_reviews.csv', mode='a', index=False, header=False)
            
            
    def retrieve_direct_reviews(self):
        def get_id(image_path):
            id = image_path.split('/')[-1]
            id = id.split('.')[0]
            return id
        
        clip = CLIP()
        df = []
        df_review = pd.read_pickle('/home/yamanishi/project/trip_recommend/data/jalan/review/review_all_period_.pkl')
        df_retrieved = pd.read_csv('../data/retrieved_reviews.csv', names=['spot_name', 'image_path', 'nearest_review', 'ind'])
        spot_names = df_retrieved['spot_name'].values
        for spot_name in tqdm(self.text_image_df['spot_name'].unique()):
            if spot_name in spot_names:continue
            df_tmp = self.text_image_df[self.text_image_df['spot_name']==spot_name]
            spot_images = [os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg') for i in range(len(df_tmp))
                                                           if os.path.exists(os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg'))]
            if len(spot_images)==0:continue
            df_review_tmp = df_review[df_review['spot']==spot_name]
                
            spot_images = random.sample(spot_images, min(50, len(spot_images)))
            spot_reviews = random.sample(list(df_review_tmp['review'].values), min(1000, len(df_review_tmp)))
            if len(spot_reviews)==0:continue
            retrieved_reviews = clip.retrieve_text_from_image(spot_images, spot_reviews)
            df = pd.DataFrame({'spot_name': spot_name, 'image_path': spot_images, 'nearest_review': retrieved_reviews,})
            print(pd.DataFrame({'spot_name': spot_name, 'image_path': spot_images, 'nearest_review': retrieved_reviews,}))
            df['id'] = df['image_path'].apply(get_id)
            df.to_csv('../data/retrieved_direct_reviews.csv', mode='a', index=False, header=False)
            
    def retrieve_direct_reviews_top5(self):
        def get_id(image_path):
            id = image_path.split('/')[-1]
            id = id.split('.')[0]
            return id
        
        clip = CLIP()
        df = []
        df_review = pd.read_pickle('/home/yamanishi/project/trip_recommend/data/jalan/review/review_all_period_.pkl')
        df_retrieved = pd.read_csv('../data/retrieved_reviews.csv', names=['spot_name', 'image_path', 'nearest_review', 'ind'])
        spot_names = df_retrieved['spot_name'].values
        for spot_name in tqdm(self.popular_spots):
            if spot_name in spot_names:continue
            df_tmp = self.text_image_df[self.text_image_df['spot_name']==spot_name]
            spot_images = [os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg') for i in range(len(df_tmp))
                                                           if os.path.exists(os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg'))]
            if len(spot_images)==0:continue
            df_review_tmp = df_review[df_review['spot']==spot_name]
                
            spot_images = random.sample(spot_images, min(7, len(spot_images)))
            spot_reviews = random.sample(list(df_review_tmp['review'].values), min(1000, len(df_review_tmp)))
            if len(spot_reviews)<50:continue
            retrieved_reviews = clip.retrieve_text_from_image_topk(spot_images, spot_reviews, k=5)
            spot_images = [image_path for image_path in spot_images for _ in range(5)]
            print(retrieved_reviews)
            df = pd.DataFrame({'spot_name': spot_name, 'image_path': spot_images, 'nearest_review': retrieved_reviews,})
            print(pd.DataFrame({'spot_name': spot_name, 'image_path': spot_images, 'nearest_review': retrieved_reviews,}))
            df['id'] = df['image_path'].apply(get_id)
            df.to_csv('../data/retrieved_direct_reviews_top5_3000_10000.csv', mode='a', index=False, header=False)
        
            
    def retrieve_images(self):
        def get_id(image_path):
            id = image_path.split('/')[-1]
            id = id.split('.')[0]
            return id
        
        clip = CLIP()
        df, spot_names = [], []
        df_review = pd.read_pickle('/home/yamanishi/project/trip_recommend/data/jalan/review/review_all_period_.pkl')
        if os.path.exists('../data/retrieved_images.csv'):
            df_retrieved = pd.read_csv('../data/retrieved_images.csv', names=['spot_name', 'image_path', 'review', 'ind', "index", "title","rating", "tag","sex","age", "name","url","visit_time"])
            spot_names = df_retrieved['spot_name'].values
            print('spot_names', spot_names)
        for spot_name in tqdm(self.text_image_df['spot_name'].unique()):
            if spot_name in spot_names:continue
            df_tmp = self.text_image_df[self.text_image_df['spot_name']==spot_name]
            spot_images = [os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg') for i in range(len(df_tmp))
                                                           if os.path.exists(os.path.join(self.image_save_dir, f'{spot_name}_{i}.jpg'))]
            if len(spot_images)==0:continue
            df_review_tmp = df_review[df_review['spot']==spot_name].reset_index()
            
            spot_reviews = df_review_tmp['review'].values
            rand_index = random.sample(list(np.arange(len(spot_reviews))), min(100, len(spot_reviews)))
                
            spot_images = random.sample(spot_images, min(500, len(spot_images)))
            spot_reviews = list(spot_reviews[rand_index])
            #spot_reviews = random.sample(list(spot_reviews), min(100, len(spot_reviews)))
            if len(spot_reviews)==0:continue
            retrieved_images = clip.retrieve_image_from_text(spot_images, spot_reviews)
            #retrieved_original_reviews = [original_reviews[r] for r in spot_reviews]
            df = pd.DataFrame({'spot_name': spot_name, 'image_path': retrieved_images, 'nearest_review': spot_reviews})
            print(pd.DataFrame({'spot_name': spot_name, 'image_path': retrieved_images, 'nearest_review': spot_reviews,}))
            df['id'] = df['image_path'].apply(get_id)
            print(len(df), len(df_review_tmp[["title","rating", "tag","sex","age", "name","url","visit_time"]].loc[rand_index]) )
            df = pd.concat([df, df_review_tmp[["title","rating", "tag","sex","age", "name","url","visit_time"]].loc[rand_index].reset_index()], axis=1)
            df.to_csv('../data/retrieved_images.csv', mode='a', index=False, header=False)
            
    def prepare_splitted_reviews(self,):
        '''
        images内の各imageに対して最も近いtextをtextsから取ってくる
        '''
        df_review = pd.read_pickle('/home/yamanishi/project/trip_recommend/data/jalan/review/review_all_period_.pkl')
        spot_reviews_all = {}
        original_reviews_all = defaultdict(partial(defaultdict, str))
        for spot_name in tqdm(self.text_image_df['spot_name'].unique()):            
            df_review_tmp = df_review[df_review['spot']==spot_name]
            spot_reviews = []
            original_reviews = {}
            for review in df_review_tmp['review']:
                review_split = review.split('。')
                for r in review_split:
                    original_reviews[r]=review
                spot_reviews+=review_split
            spot_reviews_all[spot_name] = spot_reviews
            original_reviews_all[spot_name] = original_reviews
            
        with open('../data/spot_reviews.pkl', 'wb') as f:
            pickle.dump(spot_reviews_all, f)
        with open('../data/original_reviews.pkl', 'wb') as f:
            pickle.dump(original_reviews_all, f)
            
    def retrieve_and_make_data(self):
        self.retrieve_reviews()
        self.retrieve_images()
        self.make_training_data()
            
    def make_training_data(self, max_size=800000):
        training_datas = []
        training_datas = self.make_training_data_from_posneg(training_datas)
        training_datas = self.make_training_data_from_retrieved_review(training_datas)
        training_datas = self.make_training_data_from_retrieved_images(training_datas)
        if max_size is not None:
            random.shuffle(training_datas)
            training_datas = training_datas[:max_size]
        training_datas = self.make_training_data_from_spot_description(training_datas)
        #training_datas = self.make_training_data_from_context_information(training_datas)
        training_datas = self.save_training_data('../playground/data/jalan_tourism_with_review_v4.json', training_datas)
            
    def save_training_data(self, file_path, training_datas):
        with open(file_path, 'w') as f:
            json.dump(training_datas, f)
            
    def load_reviews(self, df):
        """レビューデータを読み込み、IDをキーとする辞書でレビューを返す"""
        review_shorts = dict(zip(df['id'], df['review_short']))
        review_longs = dict(zip(df['id'], df['review_long']))
        return review_shorts, review_longs
    
    def train_test_split(self, json_path):
        with open(json_path) as f:
            data = json.load(f)
            
        image_set = set([d.get('image') for d in data])
        test_image_set = set(random.sample(list(image_set), int(len(image_set)*0.1)))
        print('test image', test_image_set)
        train_data = [d for d in data if d.get('image') not in test_image_set]
        test_data = [d for d in data if d.get('image') in test_image_set]
        save_dir = os.path.dirname(json_path)
        save_json(train_data, os.path.join(save_dir, 'train.json'))
        save_json(test_data, os.path.join(save_dir, 'test.json'))
        print('train test split done')
    
    def make_training_data_from_retrieved_review(self, training_datas, ):
        print('Making training data from retrieved review')
        retrieved_df = pd.read_csv('../data/retrieved_reviews.csv', names=['spot_name', 'image_path', 'review_short', 'review_long', 'id',
                                                                 'title','rating', 'tag', 'sex', 'age', 'name', 'url', 'visit_time'])
        review_shorts, review_longs = self.load_reviews(retrieved_df)  # レビューデータを読み込む
        for i, row in tqdm(retrieved_df.iterrows(), total=retrieved_df.shape[0]):
            id = row['id']
            if not os.path.exists(f'/home/yamanishi/project/trip_recommend/data/jalan_image_with_caption/{id}.jpg'):
                continue  # テキストがNAか、画像が存在しない場合はスキップ
            image_path = f'{id}.jpg'
            instructions = [make_spot_name_promt(row["spot_name"])]
            texts = [row["spot_name"]]
            #instructions.extend([make_caption_prompt(row["spot_name"])])
            #texts.extend([row['text']] if not pd.isna(row['text']) else [])

            # レビューが存在する場合は追加
            if id in review_shorts:
                instructions.extend([make_review_prompt(row["spot_name"], short=True), 
                                     make_review_context_prompt(row["spot_name"], row['tag'], row['sex'], row['age'])])
                texts.extend([review_shorts[id], review_longs[id]])

            if instructions:
                training_datas.append(make_training_dict(id, image_path, instructions, texts))

        return training_datas
    
    def make_training_data_from_retrieved_images(self, training_datas):
        print('Making training data from retrieved images')
        retrieved_image_df = pd.read_csv('/home/yamanishi/project/airport/src/analysis/LLaVA/data/retrieved_image_per_3text.csv', names=['spot_name', 'image_path', 'review', 'ind', "index", "title","rating", "tag","sex","age", "name","url","visit_time"])
        retrieved_image_df = retrieved_image_df

        for _, row in tqdm(retrieved_image_df.iterrows(), total=retrieved_image_df.shape[0]):
            ind = row['ind']
            if not os.path.exists(os.path.join(self.image_save_dir, f'{ind}.jpg')):continue  
            # テキストがNAまたは画像が存在しない場合はスキップ

            spot_name = row['spot_name'].replace('/', '')
            id = f'{row["ind"]}_retrieved_from_image'
            image_path = f'{row["ind"]}.jpg'
            instructions = [make_spot_name_promt(row["spot_name"])]
            texts = [row["spot_name"]]
            instructions = [make_review_context_prompt(spot_name, row['tag'], row['sex'], row['age'])]
            texts = [row['review']]

            training_datas.append(make_training_dict(id, image_path, instructions, texts))

        print(f'Current training data num: {len(training_datas)}')
        return training_datas
    
    def make_conversation_pair(self):
        llm = LLM()
        df = pd.read_csv('/home/yamanishi/project/airport/src/analysis/LLaVA/data/retrieved_direct_reviews_top5_3000_10000.csv', names=['spot_name', 'image_path', 'review', 'id'])
        batch_size=50
        outputs = []
        for i in tqdm(range(len(df)//batch_size+1)):
            reviews = df[i*batch_size:(i+1)*batch_size]['review'].values
            prompts = []
            for review in reviews:
                if pd.isna(review):review=''
                prompt = prompt_qa+review
                #print(prompt)
                prompts.append(prompt)
            outputs+=llm.generate(prompts)
            #print('outputs', outputs)
        df['qa'] = outputs
        df.to_csv('/home/yamanishi/project/airport/src/analysis/LLaVA/data/retrieved_direct_reviews_top5_qa_3000_10000.csv')
              
    def make_conversation_data(self):
        with open('/home/yamanishi/project/airport/src/analysis/LLaVA/playground/data/v4/train_conv.json') as f:
            train_data = json.load(f)
        with open('/home/yamanishi/project/airport/src/analysis/LLaVA/playground/data/v4/test_conv.json') as f:
            test_data = json.load(f)
        train_image_set = set([d.get('image') for d in train_data])
        spot_names = [d['id'].split('_')[0] for d in train_data] + [d['id'].split('_')[0] for d in test_data]
        spot_names_set = set(spot_names)
        spot2ind = {spot:i for i,spot in enumerate(spot_names_set)}
        #print(train_image_set)
        df = pd.read_csv('/home/yamanishi/project/airport/src/analysis/LLaVA/data/retrieved_direct_reviews_top5_qa_3000_10000.csv', names=['spot_name', 'image_path', 'review', 'id','qa'])
        print(df['qa'].head())
        for i,(image_path, group) in tqdm(enumerate(df.groupby('image_path'))):
            image_path = os.path.basename(image_path)
            spot_name = image_path.split('_')[0]
            id = image_path.split('.')[0] + '_conversation'
            instructions, texts = [], []
            for i,qa in enumerate(group['qa'].values):
                if pd.isna(qa):continue
                qa = qa.split('\n')
                if len(qa)<2:continue
                if spot_name not in spot2ind:continue
                if i==0:
                    #instructions.append(f'画像が示す場所は{spot_name}<poi{spot2ind[spot_name]}>です。この観光地に関する次のいくつかの質問に答えてください。'+qa[0])
                    instructions.append(f'画像が示す場所は{spot_name}です。この観光地に関する次のいくつかの質問に答えてください。'+qa[0])
                else:instructions.append(qa[0])
                texts.append(qa[1].replace('<|im_end|>', ''))
            #print(make_training_dict(id, image_path, instructions, texts))
            if not len(instructions):continue
            if image_path in train_image_set:
                #print('train')
                train_data.append(make_training_dict(id, image_path, instructions, texts))
            else:
                test_data.append(make_training_dict(id, image_path, instructions, texts))
            #if i==10:break
        with open('/home/yamanishi/project/airport/src/analysis/LLaVA/playground/data/v4/train_conv2.json', 'w') as f:
            json.dump(train_data, f)
        with open('/home/yamanishi/project/airport/src/analysis/LLaVA/playground/data/v4/test_conv2.json', 'w') as f:
            json.dump(test_data, f)

    def load_context_data(self):
        base_path = '/home/yamanishi/project/trip_recommend/data/jalan/graph'
        contexts = {
            'age': np.load(f'{self.graph_dir}/age_contexts.npy'),
            'gender': np.load(f'{self.graph_dir}/sex_contexts.npy'),
            'season': np.load(f'{self.graph_dir}/season_contexts.npy'),
            'people': np.load(f'{self.graph_dir}/people_contexts.npy'),
            'time': np.load(f'{self.graph_dir}/time_contexts.npy')
        }
        # 上位N個のコンテキストを取得
        for key, context in contexts.items():
            top_indices = np.argsort(-context)[:, :2] if key != 'gender' else np.argsort(-context)[:, :1]
            contexts[key] = top_indices
        return contexts
    
    def make_training_data_from_context_information(self, training_datas):
        print('Making training data from spot context information')
        contexts = self.load_context_data()

        for i,spot_name in tqdm(enumerate(self.experiment_df['spot_name'].values)):
            context_data = {key: contexts[key][i] for _, key in enumerate(['age', 'gender', 'season', 'people', 'time'])}
            instructions = [make_context_prompt(spot_name)]
            texts = [make_context_answer(spot_name, context_data['age'], context_data['gender'],
                                         context_data['season'], context_data['people'], context_data['time'])]
            id = f'{spot_name}_context'
            training_datas.append(make_training_dict(id, image=None, instructions=instructions, texts=texts))

        print(f'Current training data num: {len(training_datas)}')
        return training_datas
            

    def make_training_data_from_spot_description(self, training_datas):
        with open('/home/yamanishi/project/airport/src/data/experiment.pkl', 'rb') as f:
            experiment_df = pickle.load(f)
        self.experiment_df = experiment_df
        for _, row in tqdm(experiment_df.iterrows(), total=experiment_df.shape[0]):
            spot_name, description = row['spot_name'], row['description']
            instructions = [make_description_prompt(spot_name)]
            texts = [description]
            id = f'{spot_name}_description'
            training_datas.append(make_training_dict(id, image=None, instructions=instructions, texts=texts))
        
        print(f'Current training data num: {len(training_datas)}')
        return training_datas
    
    def make_training_data_from_posneg(self, training_datas):
        posneg = load_multiple_dict([f'/home/yamanishi/project/airport/src/data/review/spot/goodbad_all_period_{i}.pkl' for i in range(7)])
        print('Making training data from posneg review')
        retrieved_review_df = pd.read_csv('/home/yamanishi/project/airport/src/analysis/LLaVA/data/retrieved_direct_reviews.csv',)
        for _, row in tqdm(retrieved_review_df.iterrows(), total=retrieved_review_df.shape[0]):
            ind = row['ind']
            if not os.path.exists(os.path.join(self.image_save_dir, f'{ind}.jpg')):continue  
            # テキストがNAまたは画像が存在しない場合はスキップ

            spot_name = row['spot_name'].replace('/', '')
            id = f'{row["ind"]}_posneg'
            image_path = f'{row["ind"]}.jpg'
            instructions = [make_spot_name_promt(row["spot_name"])]
            texts = [row["spot_name"]]
            posneg_tmp = posneg[row['index']]
            matches = re.findall(r'「([^」]+)」', posneg_tmp)
            instructions = [make_review_context_posneg_prompt(spot_name, row['tag'], row['sex'], row['age'], matches)]
            texts = [row['review']]
            training_datas.append(make_training_dict(id, image_path, instructions, texts))

        print(f'Current training data num: {len(training_datas)}')
        return training_datas
    
    @staticmethod
    def _make_rec_conv(spots, image_paths, titles, review_spots, reviews, test_spot, random_spots):    
        convs = []
        conv_user = {}
        conv_user['from'] = 'human'
        conv_user['value'] = '次はユーザーが訪問した場所でとった写真とタイトルです。'
        for i, image_path in enumerate(image_paths):
            conv_user['value']+=spots[i]+'\n'
            conv_user['value']+=f'<image{i}>\n'
            if titles[i] is None or pd.isna(titles[i]):continue
            conv_user['value']+=titles[i]
        conv_user['value']+='次はユーザーが作成したレビューです'
        for i,(review_spot,review) in enumerate(zip(review_spots, reviews)):
            conv_user['value'] += review_spot
            conv_user['value'] += review
            
        conv_user['value']+='次にユーザーが訪問する場所を次の中から推測してください\n'
        all_spots = [test_spot] + random_spots
        random.shuffle(all_spots)
        conv_user['value']+='\n'.join(all_spots)
        convs.append(conv_user)
        
        conv_gpt = {}
        conv_gpt['from'] = 'gpt'
        conv_gpt['value'] = f'{test_spot}'
        convs.append(conv_gpt)
        return convs
    
    def download_images_user_text(self):
        #df =pd.read_csv('/home/yamanishi/project/trip_recommend/data/jalan/spot/text_image_user_pairs.csv',
        #              names=['image_url', 'text', 'user','spot_name', 'ind'])
        
        df = pd.read_csv('./recommend/filtered_image_df.csv')
        for spot_name,image_url in tqdm(zip(df['spot_name'], df['image_url'])):
            if pd.isna(spot_name) or pd.isna(image_url):continue
            suffix = image_url.split('/')[-1]
            os.makedirs(f'/home/yamanishi/project/airport/src/data/jalan_image/{spot_name}/', exist_ok=True)
            download_path = f'/home/yamanishi/project/airport/src/data/jalan_image/{spot_name}/{suffix}'
            download_path = download_path.replace('jpeg', 'jpg')
            #print(spot_name)
            if not os.path.exists(download_path):
                print(spot_name)
                try:
                    urlretrieve(image_url, download_path)
                    time.sleep(1)
                except urllib.error.HTTPError:
                    continue
                
    
if __name__=='__main__':
    parser = argparse.ArgumentParser(description="Data Preprocessor Utility")
    parser.add_argument('-f', default='download_images', help='Function to run')
    parser.add_argument('--ind', type=int, default=0)
    parser.add_argument('--json_path', type=str, default='')
    args = parser.parse_args()

    # DataPreprocessorのインスタンスを作成
    preprocessor = DataPreprocessor()
    #preprocessor.retrieve_direct_reviews_top5()
    #preprocessor.make_conversation_pair()
    # function引数に基づいて対応するメソッドを実行
    if args.f == 'download_images':
        preprocessor.download_images(args.ind*800000, (args.ind+1)*800000)
    elif args.f == 'retrieve_reviews':
        preprocessor.retrieve_reviews()
    elif args.f == 'retrieve_direct_reviews':
        preprocessor.retrieve_direct_reviews()
    elif args.f =='retrieve_images':
        preprocessor.retrieve_images()
    elif args.f == 'make_training_data':
        preprocessor.make_training_data(max_size=None)
    elif args.f == 'prepare_splitted_reviews':
        preprocessor.prepare_splitted_reviews()
    elif args.f == 'make_training_data_with_review':
        preprocessor.make_training_data_with_review()
    elif args.f == 'retrieve_and_make_data':
        preprocessor.retrieve_and_make_data()
    elif args.f == 'train_test_split':
        preprocessor.train_test_split(args.json_path)
    elif args.f == 'retrieve_direct_reviews_top5':
        preprocessor.retrieve_direct_reviews_top5()
    elif args.f == 'make_conversation_pair':
        preprocessor.make_conversation_pair()
    elif  args.f == 'make_conversation_data':
        preprocessor.make_conversation_data()
    elif args.f == 'download_images_user_text':
        preprocessor.download_images_user_text()
    else:
        print(f"Function {args.f} is not recognized.")