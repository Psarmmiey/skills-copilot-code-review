"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
import logging

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)

# Configure logging to only log on server
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.get("/active")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements that should be displayed now"""
    try:
        current_time = datetime.now().isoformat()
        
        # Find announcements that are active and within their time range
        query = {
            "active": True,
            "$or": [
                {"start_date": None},  # No start date means immediately active
                {"start_date": {"$lte": current_time}}  # Start date has passed
            ],
            "end_date": {"$gte": current_time}  # End date hasn't passed
        }
        
        announcements = list(announcements_collection.find(query).sort("created_at", -1))
        
        # Convert ObjectId to string for JSON serialization
        for announcement in announcements:
            if "_id" in announcement:
                announcement["_id"] = str(announcement["_id"])
        
        return announcements
    except Exception as e:
        logger.error(f"Error fetching active announcements: {e}")
        # Return empty list on error, don't propagate to frontend
        return []


@router.get("/all")
def get_all_announcements(teacher_username: str) -> List[Dict[str, Any]]:
    """Get all announcements for management (requires teacher authentication)"""
    try:
        # Verify teacher exists and is authenticated
        teacher = teachers_collection.find_one({"_id": teacher_username})
        if not teacher:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get all announcements
        announcements = list(announcements_collection.find({}).sort("created_at", -1))
        
        # Convert ObjectId to string for JSON serialization
        for announcement in announcements:
            if "_id" in announcement:
                announcement["_id"] = str(announcement["_id"])
        
        return announcements
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching all announcements: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch announcements")


@router.post("/create")
def create_announcement(
    message: str,
    end_date: str,
    teacher_username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement"""
    try:
        # Verify teacher exists and is authenticated
        teacher = teachers_collection.find_one({"_id": teacher_username})
        if not teacher:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate dates
        try:
            datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if start_date:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        
        # Create announcement document
        announcement_doc = {
            "message": message.strip(),
            "start_date": start_date,
            "end_date": end_date,
            "created_by": teacher_username,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        result = announcements_collection.insert_one(announcement_doc)
        
        # Return the created announcement
        announcement_doc["_id"] = str(result.inserted_id)
        
        logger.info(f"Announcement created by {teacher_username}")
        return {
            "message": "Announcement created successfully",
            "announcement": announcement_doc
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating announcement: {e}")
        raise HTTPException(status_code=500, detail="Failed to create announcement")


@router.put("/update/{announcement_id}")
def update_announcement(
    announcement_id: str,
    message: str,
    end_date: str,
    teacher_username: str,
    start_date: Optional[str] = None,
    active: bool = True
) -> Dict[str, Any]:
    """Update an existing announcement"""
    try:
        # Verify teacher exists and is authenticated
        teacher = teachers_collection.find_one({"_id": teacher_username})
        if not teacher:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate ObjectId
        try:
            obj_id = ObjectId(announcement_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid announcement ID")
        
        # Validate dates
        try:
            datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if start_date:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        
        # Update announcement
        update_doc = {
            "message": message.strip(),
            "start_date": start_date,
            "end_date": end_date,
            "active": active
        }
        
        result = announcements_collection.update_one(
            {"_id": obj_id},
            {"$set": update_doc}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        logger.info(f"Announcement {announcement_id} updated by {teacher_username}")
        return {"message": "Announcement updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating announcement: {e}")
        raise HTTPException(status_code=500, detail="Failed to update announcement")


@router.delete("/delete/{announcement_id}")
def delete_announcement(announcement_id: str, teacher_username: str) -> Dict[str, Any]:
    """Delete an announcement"""
    try:
        # Verify teacher exists and is authenticated
        teacher = teachers_collection.find_one({"_id": teacher_username})
        if not teacher:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate ObjectId
        try:
            obj_id = ObjectId(announcement_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid announcement ID")
        
        # Delete announcement
        result = announcements_collection.delete_one({"_id": obj_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        logger.info(f"Announcement {announcement_id} deleted by {teacher_username}")
        return {"message": "Announcement deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting announcement: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete announcement")


@router.put("/toggle/{announcement_id}")
def toggle_announcement_status(announcement_id: str, teacher_username: str) -> Dict[str, Any]:
    """Toggle the active status of an announcement"""
    try:
        # Verify teacher exists and is authenticated
        teacher = teachers_collection.find_one({"_id": teacher_username})
        if not teacher:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate ObjectId
        try:
            obj_id = ObjectId(announcement_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid announcement ID")
        
        # Get current announcement
        announcement = announcements_collection.find_one({"_id": obj_id})
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        # Toggle active status
        new_status = not announcement.get("active", True)
        result = announcements_collection.update_one(
            {"_id": obj_id},
            {"$set": {"active": new_status}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        status_text = "activated" if new_status else "deactivated"
        logger.info(f"Announcement {announcement_id} {status_text} by {teacher_username}")
        
        return {
            "message": f"Announcement {status_text} successfully",
            "active": new_status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling announcement status: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle announcement status")