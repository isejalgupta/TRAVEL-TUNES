"""
Song data for TripTunes - the full library from the original console app.

seed_songs() loads all 100 songs into the database on startup, and is
idempotent (skips if songs already exist).
"""

from database import SessionLocal, Song as SongRow


SONGS = [
    ('Badtameez Dil', 'Benny Dayal', 'Bollywood', 'Happy', 4.7),
    ('Gallan Goodiyaan', 'Shankar Mahadevan', 'Bollywood', 'Happy', 4.8),
    ('London Thumakda', 'Labh Janjua', 'Bollywood', 'Happy', 4.7),
    ('Nagada Sang Dhol', 'Shreya Ghoshal', 'Bollywood', 'Happy', 4.6),
    ('Balam Pichkari', 'Shalmali Kholgade', 'Bollywood', 'Happy', 4.5),
    ('Kar Gayi Chull', 'Fazilpuria', 'Bollywood', 'Happy', 4.5),
    ('Dil Dhadakne Do', 'Shankar Ehsaan', 'Bollywood', 'Happy', 4.6),
    ('Dhinka Chika', 'Neeraj Shridhar', 'Bollywood', 'Happy', 4.4),
    ('Senorita', 'Shaan', 'Bollywood', 'Happy', 4.5),
    ('Zindagi Na Milegi Dobara', 'Shankar Mahadevan', 'Bollywood', 'Happy', 4.8),
    ('Jai Ho', 'A.R. Rahman', 'Bollywood', 'Happy', 4.9),
    ('Vande Mataram', 'A.R. Rahman', 'Patriotic', 'Happy', 5.0),
    ('Maa Tujhe Salaam', 'A.R. Rahman', 'Patriotic', 'Happy', 4.9),
    ('Rang De Basanti', 'Daler Mehndi', 'Bollywood', 'Happy', 4.7),
    ('Zinda', 'Siddharth Mahadevan', 'Bollywood', 'Happy', 4.8),
    ('Nashe Si Chadh Gayi', 'Arijit Singh', 'Bollywood', 'Happy', 4.6),
    ('Swag Se Swagat', 'Vishal Dadlani', 'Bollywood', 'Happy', 4.5),
    ('Photocopy', 'Anushka Manchanda', 'Bollywood', 'Happy', 4.4),
    ('Naatu Naatu', 'Rahul Sipligunj', 'Telugu', 'Happy', 5.0),
    ('G.O.A.T', 'Diljit Dosanjh', 'Punjabi', 'Happy', 4.7),
    ('Lover', 'Diljit Dosanjh', 'Punjabi', 'Happy', 4.6),
    ('Lahore', 'Guru Randhawa', 'Punjabi', 'Happy', 4.5),
    ('Morni Banke', 'Neha Kakkar', 'Bollywood', 'Happy', 4.4),
    ('Unakenna Venum Sollu', 'Anirudh Ravichander', 'Tamil', 'Happy', 4.6),
    ('Saibo', 'Shreya Ghoshal', 'Bollywood', 'Happy', 4.7),
    ('Tum Hi Ho', 'Arijit Singh', 'Bollywood', 'Emotional', 4.9),
    ('Channa Mereya', 'Arijit Singh', 'Bollywood', 'Emotional', 4.9),
    ('Kal Ho Naa Ho', 'Sonu Nigam', 'Bollywood', 'Emotional', 4.8),
    ('Ae Dil Hai Mushkil', 'Arijit Singh', 'Bollywood', 'Emotional', 4.7),
    ('Kabhi Alvida Naa Kehna', 'Sonu Nigam', 'Bollywood', 'Emotional', 4.7),
    ('Dil To Pagal Hai', 'Lata Mangeshkar', 'Bollywood', 'Emotional', 4.8),
    ('Phir Le Aya Dil', 'Rekha Bhardwaj', 'Bollywood', 'Emotional', 4.6),
    ('Hamari Adhuri Kahani', 'Arijit Singh', 'Bollywood', 'Emotional', 4.6),
    ('Dard Dilo Ke', 'Mohammed Irfan', 'Bollywood', 'Emotional', 4.5),
    ('Main Dhoondne Ko Zamaane', 'Arijit Singh', 'Bollywood', 'Emotional', 4.6),
    ('Jeena Jeena', 'Atif Aslam', 'Bollywood', 'Emotional', 4.7),
    ('O Saathi', 'Atif Aslam', 'Bollywood', 'Emotional', 4.6),
    ('Tera Hone Laga Hoon', 'Atif Aslam', 'Bollywood', 'Emotional', 4.5),
    ('Bulleya', 'Amit Mishra', 'Sufi', 'Emotional', 4.8),
    ('Ik Onkar', 'Harshdeep Kaur', 'Sufi', 'Emotional', 4.9),
    ('Dil Diyan Gallan', 'Atif Aslam', 'Indie', 'Emotional', 4.7),
    ('Pasoori', 'Ali Sethi', 'Indie', 'Emotional', 5.0),
    ('Ve Maahi', 'Arijit Singh', 'Bollywood', 'Emotional', 4.8),
    ('Agar Tum Saath Ho', 'Arijit Singh', 'Bollywood', 'Emotional', 4.9),
    ('Chaiyya Chaiyya', 'Sukhwinder Singh', 'Bollywood', 'Emotional', 5.0),
    ('Kannazhaga', 'Shreya Ghoshal', 'Tamil', 'Emotional', 4.8),
    ('Vathikkalu Vathikkalu', 'K.S. Chithra', 'Malayalam', 'Emotional', 4.7),
    ('Nenjukkul Peidhidum', 'Harris Jayaraj', 'Tamil', 'Emotional', 4.8),
    ('Kesariya', 'Arijit Singh', 'Bollywood', 'Emotional', 4.9),
    ('Raabta', 'Arijit Singh', 'Bollywood', 'Emotional', 4.5),
    ('Tujh Mein Rab Dikhta Hai', 'Roop Kumar Rathod', 'Bollywood', 'Romantic', 4.9),
    ('Pehla Nasha', 'Udit Narayan', 'Bollywood', 'Romantic', 5.0),
    ('Lag Ja Gale', 'Lata Mangeshkar', 'Bollywood', 'Romantic', 5.0),
    ('Kuch Kuch Hota Hai', 'Udit Narayan', 'Bollywood', 'Romantic', 4.9),
    ('Tere Liye', 'Atif Aslam', 'Bollywood', 'Romantic', 4.7),
    ('Sun Saathiya', 'Shreya Ghoshal', 'Bollywood', 'Romantic', 4.6),
    ('Teri Meri Prem Kahani', 'Udit Narayan', 'Bollywood', 'Romantic', 4.6),
    ('Jab Se Tere Naina', 'Udit Narayan', 'Bollywood', 'Romantic', 4.7),
    ('Soch Na Sake', 'Arijit Singh', 'Punjabi', 'Romantic', 4.7),
    ('Enna Sona', 'Arijit Singh', 'Bollywood', 'Romantic', 4.8),
    ('Dil Ko Karaar Aaya', 'Neha Kakkar', 'Bollywood', 'Romantic', 4.6),
    ('Hawayein', 'Arijit Singh', 'Bollywood', 'Romantic', 4.9),
    ('Rehnaa Hai Terre Dil Mein', 'Rehman', 'Bollywood', 'Romantic', 4.8),
    ('Pehli Baar Mohabbat', 'Mohit Chauhan', 'Bollywood', 'Romantic', 4.7),
    ('Abhi Mujh Mein Kahin', 'Sonu Nigam', 'Bollywood', 'Romantic', 4.8),
    ('Tera Ban Jaunga', 'Akhil Sachdeva', 'Bollywood', 'Romantic', 4.7),
    ('Apna Bana Le', 'Arijit Singh', 'Bollywood', 'Romantic', 4.7),
    ('Mere Haath Mein', 'Udit Narayan', 'Bollywood', 'Romantic', 4.6),
    ('Tere Sang Yaara', 'Atif Aslam', 'Bollywood', 'Romantic', 4.7),
    ('Kho Gaye Hum Kahan', 'Jasleen Royal', 'Indie', 'Romantic', 4.8),
    ('Mahi Ve', 'Udit Narayan', 'Bollywood', 'Romantic', 4.7),
    ('Ilahi', 'Mohit Chauhan', 'Bollywood', 'Romantic', 4.6),
    ('Manike Mage Hithe', 'Yohani', 'Indie', 'Romantic', 4.6),
    ('Kalank', 'Arijit Singh', 'Bollywood', 'Romantic', 4.5),
    ('Tujhe Kitna Chahne Lage', 'Arijit Singh', 'Bollywood', 'Romantic', 4.9),
    ('Lungi Dance', 'Honey Singh', 'Bollywood', 'Party', 4.6),
    ('Angrezi Beat', 'Honey Singh', 'Punjabi', 'Party', 4.5),
    ('Party All Night', 'Honey Singh', 'Punjabi', 'Party', 4.5),
    ('Desi Beat', 'Honey Singh', 'Punjabi', 'Party', 4.4),
    ('Hookah Bar', 'Akshay Kumar', 'Bollywood', 'Party', 4.4),
    ('Dancefloor', 'Badshah', 'Punjabi', 'Party', 4.5),
    ('Abcd', 'Badshah', 'Punjabi', 'Party', 4.6),
    ('DJ Waley Babu', 'Badshah', 'Punjabi', 'Party', 4.5),
    ('Garmi', 'Badshah', 'Bollywood', 'Party', 4.6),
    ('Paagal', 'Badshah', 'Punjabi', 'Party', 4.5),
    ('Kala Chashma', 'Baar Baar Dekho', 'Bollywood', 'Party', 4.7),
    ('Saturday Saturday', 'Indeep Bakshi', 'Bollywood', 'Party', 4.5),
    ('Malhari', 'Vishal Dadlani', 'Bollywood', 'Party', 4.8),
    ('Tattad Tattad', 'Aditya Narayan', 'Bollywood', 'Party', 4.5),
    ('Bhaag DK Bose', 'Raghu Dixit', 'Bollywood', 'Party', 4.4),
    ('Ainvayi Ainvayi', 'Salim Merchant', 'Bollywood', 'Party', 4.5),
    ('Jhoome Jo Pathaan', 'Arijit Singh', 'Bollywood', 'Party', 4.6),
    ('Besharam Rang', 'Caralisa Monteiro', 'Bollywood', 'Party', 4.5),
    ('Ghungroo', 'Arijit Singh', 'Bollywood', 'Party', 4.7),
    ('Oo Antava', 'Indravathi Chauhan', 'Telugu', 'Party', 4.7),
    ('Bijlee Bijlee', 'Harrdy Sandhu', 'Punjabi', 'Party', 4.6),
    ('Koka', 'Diljit Dosanjh', 'Punjabi', 'Party', 4.5),
    ('Patiala Peg', 'Diljit Dosanjh', 'Punjabi', 'Party', 4.5),
    ('Amplifier', 'Imran Khan', 'Punjabi', 'Party', 4.6),
    ('Kar Har Maidaan Fateh', 'Sukhwinder Singh', 'Bollywood', 'Party', 4.8),
]


def seed_songs():
    db = SessionLocal()
    try:
        if db.query(SongRow).first() is not None:
            return
        for name, artist, genre, mood, rating in SONGS:
            db.add(SongRow(name=name, artist=artist, genre=genre, mood=mood, rating=rating))
        db.commit()
    finally:
        db.close()