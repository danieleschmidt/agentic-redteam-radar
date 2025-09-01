"""
Real Data Processing Pipeline Implementation
"""
import asyncio
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProcessingResult:
    id: str
    input_data: Any
    output_data: Optional[Any]
    status: ProcessingStatus
    processing_time: float
    timestamp: datetime
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

class DataPipeline:
    """
    Async data processing pipeline with real functionality
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.queue = asyncio.Queue()
        self.results = {}
        self.processors = []
        self.running = False
        
    def add_processor(self, processor: Callable) -> 'DataPipeline':
        """Add a processing step to the pipeline"""
        self.processors.append(processor)
        return self
        
    async def process_item(self, data: Any) -> ProcessingResult:
        """Process a single item through the pipeline"""
        start_time = datetime.now()
        item_id = self._generate_id(data)
        
        result = ProcessingResult(
            id=item_id,
            input_data=data,
            output_data=None,
            status=ProcessingStatus.PROCESSING,
            processing_time=0,
            timestamp=start_time
        )
        
        try:
            # Run through all processors
            current_data = data
            for processor in self.processors:
                if asyncio.iscoroutinefunction(processor):
                    current_data = await processor(current_data)
                else:
                    current_data = processor(current_data)
            
            result.output_data = current_data
            result.status = ProcessingStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            result.status = ProcessingStatus.FAILED
            result.error = str(e)
        
        finally:
            result.processing_time = (datetime.now() - start_time).total_seconds()
            self.results[item_id] = result
            
        return result
    
    async def process_batch(self, items: List[Any]) -> List[ProcessingResult]:
        """Process multiple items concurrently"""
        tasks = [self.process_item(item) for item in items]
        return await asyncio.gather(*tasks)
    
    async def start_workers(self):
        """Start worker pool for continuous processing"""
        self.running = True
        workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]
        await asyncio.gather(*workers)
    
    async def _worker(self, name: str):
        """Worker coroutine"""
        while self.running:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                result = await self.process_item(item)
                logger.info(f"{name} processed item {result.id}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"{name} error: {e}")
    
    def _generate_id(self, data: Any) -> str:
        """Generate unique ID for data"""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        total = len(self.results)
        if total == 0:
            return {"total": 0}
        
        completed = sum(1 for r in self.results.values() 
                       if r.status == ProcessingStatus.COMPLETED)
        failed = sum(1 for r in self.results.values() 
                    if r.status == ProcessingStatus.FAILED)
        avg_time = sum(r.processing_time for r in self.results.values()) / total
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total,
            "avg_processing_time": avg_time
        }

# Processing functions
def transform_data(data: Dict) -> Dict:
    """Transform data structure"""
    return {
        **data,
        "transformed": True,
        "transform_time": datetime.now().isoformat(),
        "hash": hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:8]
    }

def validate_data(data: Dict) -> Dict:
    """Validate and clean data"""
    required_fields = ["id", "type", "value"]
    for field in required_fields:
        if field not in data:
            data[field] = None
    
    # Clean and validate
    if isinstance(data.get("value"), str):
        data["value"] = data["value"].strip()
    
    data["validated"] = True
    return data

async def enrich_data(data: Dict) -> Dict:
    """Async data enrichment"""
    await asyncio.sleep(0.1)  # Simulate API call
    
    data["enriched"] = {
        "timestamp": datetime.now().isoformat(),
        "source": "internal",
        "confidence": 0.95,
        "metadata": {
            "processor": "v2.0",
            "region": "us-east-1"
        }
    }
    return data

# Example usage
async def main():
    # Create pipeline
    pipeline = DataPipeline(max_workers=3)
    pipeline.add_processor(validate_data)
    pipeline.add_processor(transform_data)
    pipeline.add_processor(enrich_data)
    
    # Process batch
    test_data = [
        {"id": i, "type": "sensor", "value": f"reading_{i}"}
        for i in range(10)
    ]
    
    results = await pipeline.process_batch(test_data)
    
    # Print results
    for result in results:
        if result.status == ProcessingStatus.COMPLETED:
            print(f"✓ {result.id}: {result.processing_time:.3f}s")
        else:
            print(f"✗ {result.id}: {result.error}")
    
    # Print stats
    stats = pipeline.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
