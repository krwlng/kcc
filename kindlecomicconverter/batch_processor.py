import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from loguru import logger
from .comic2ebook import Comic2Ebook
from .shared import getImageFileName

class BatchProcessor:
    def __init__(self, max_workers: int = None):
        """
        Batch işleme için sınıf.
        
        Args:
            max_workers: Maksimum paralel işlem sayısı. None ise CPU sayısı kadar kullanılır.
        """
        self.max_workers = max_workers
        self.current_tasks = []
        self.results = []
        
    def process_directory(self, input_dir: str, output_dir: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Bir dizindeki tüm desteklenen dosyaları işler.
        
        Args:
            input_dir: Girdi dizini
            output_dir: Çıktı dizini
            options: Dönüştürme seçenekleri
            
        Returns:
            İşlem sonuçlarının listesi
        """
        logger.info(f"Starting batch processing for directory: {input_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Desteklenen dosyaları bul
        files_to_process = []
        for root, _, files in os.walk(input_dir):
            for file in files:
                if self._is_supported_file(file):
                    input_path = os.path.join(root, file)
                    output_path = os.path.join(output_dir, os.path.splitext(file)[0] + ".mobi")
                    files_to_process.append((input_path, output_path))
        
        logger.info(f"Found {len(files_to_process)} files to process")
        
        # İşlemleri paralel olarak başlat
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for input_path, output_path in files_to_process:
                future = executor.submit(self._process_single_file, input_path, output_path, options)
                futures.append(future)
            
            # İlerleme çubuğu ile işlemleri takip et
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing files"):
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}")
                    self.results.append({"status": "error", "error": str(e)})
        
        logger.info("Batch processing completed")
        return self.results
    
    def _process_single_file(self, input_path: str, output_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tek bir dosyayı işler.
        
        Args:
            input_path: Girdi dosyası yolu
            output_path: Çıktı dosyası yolu
            options: Dönüştürme seçenekleri
            
        Returns:
            İşlem sonucu
        """
        logger.debug(f"Processing file: {input_path}")
        try:
            # Comic2Ebook sınıfını kullanarak dönüştürme işlemini gerçekleştir
            comic = Comic2Ebook(input_path, output_path, options)
            comic.makeBook()
            
            return {
                "status": "success",
                "input": input_path,
                "output": output_path
            }
        except Exception as e:
            logger.error(f"Error processing {input_path}: {str(e)}")
            return {
                "status": "error",
                "input": input_path,
                "error": str(e)
            }
    
    def _is_supported_file(self, filename: str) -> bool:
        """
        Dosyanın desteklenip desteklenmediğini kontrol eder.
        """
        return getImageFileName(filename) is not None or filename.lower().endswith(('.cbz', '.cbr', '.cb7', '.pdf'))
    
    def get_progress(self) -> float:
        """
        Toplam ilerlemeyi döndürür (0-100 arası)
        """
        if not self.current_tasks:
            return 0
        completed = sum(1 for task in self.current_tasks if task.done())
        return (completed / len(self.current_tasks)) * 100 