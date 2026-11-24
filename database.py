import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "velaiconnect"),
        autocommit=False
    )

def init_db():
    """Create tables if they do not already exist. Database itself must exist first."""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(120) NOT NULL,
      phone VARCHAR(25) NOT NULL UNIQUE,
      email VARCHAR(160) UNIQUE,
      password_hash VARCHAR(255) NOT NULL,
      role ENUM('worker','employer') NOT NULL,
      language VARCHAR(40) DEFAULT 'English',
      city VARCHAR(100),
      skills TEXT,
      experience VARCHAR(100),
      verified TINYINT(1) DEFAULT 0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
      id INT AUTO_INCREMENT PRIMARY KEY,
      employer_id INT NOT NULL,
      title VARCHAR(160) NOT NULL,
      description TEXT NOT NULL,
      city VARCHAR(100) NOT NULL,
      wage DECIMAL(10,2) NOT NULL,
      wage_period ENUM('hour','day','week','month') DEFAULT 'day',
      hours VARCHAR(80) NOT NULL,
      skills TEXT,
      contact VARCHAR(100),
      status ENUM('open','closed') DEFAULT 'open',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (employer_id) REFERENCES users(id) ON DELETE CASCADE,
      INDEX idx_jobs_city_status (city, status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
      id INT AUTO_INCREMENT PRIMARY KEY,
      job_id INT NOT NULL,
      worker_id INT NOT NULL,
      message TEXT,
      status ENUM('submitted','reviewing','accepted','rejected') DEFAULT 'submitted',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY unique_application (job_id, worker_id),
      FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
      FOREIGN KEY (worker_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    db.commit()
    cur.close(); db.close()
