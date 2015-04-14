from podaci import PodaciView
from django.http import StreamingHttpResponse
#from django.contrib.auth.models import User
from django.contrib.auth import get_user_model # as per https://docs.djangoproject.com/en/dev/topics/auth/customizing/#referencing-the-user-model
from django.template.loader import render_to_string
from copy import copy
from podaci.filesystem import File, Tag, FileNotFound

class Create(PodaciView):
    template_name = "podaci/files/create.jinja"

    def get_context_data(self):
        f = File(self.fs)
        # print "POST:", self.request.POST
        # print "FILES:", self.request.FILES
        uploadedfile = self.request.FILES.get("files[]", "")
        if uploadedfile == "":
            return None
        res = f.create_from_filehandle(uploadedfile)
        tag = self.request.POST.get("tag", None)
        if tag:
            res.add_tag(tag)
        return res


class Details(PodaciView):
    template_name = "podaci/files/details.jinja"

    def get_context_data(self, id):
        self.file = File(self.fs)
        self.file.load(id)
        users = {}
        tags = {}
        notes = []
        for user in self.file.meta["allowed_users"]:
            users[user] = get_user_model().objects.get(id=user)
        for tag in self.file.meta["tags"]:
            tags[tag] = self.fs.get_tag(tag)
        notes = copy(self.file.meta["notes"])
        for note in notes:
            u = get_user_model().objects.get(id=note["user"])
            note["user_details"] = {
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.first_name,
            }

        return {
            "file": self.file, 
            "users": users,
            "tags": tags,
            "notes": notes,
        }

class Delete(PodaciView):
    template_name = "podaci/files/create.jinja"

    def get_context_data(self, id):
        f = File(self.fs)
        try:
            f.load(id)
        except FileNotFound:
            return {"id": id, "deleted": False, "error": "notfound"}
        status = f.delete(True)
        return {"id": id, "deleted": status}

class Download(PodaciView):
    template_name = "NO_TEMPLATE"

    def get(self, request, id, **kwargs):
        f = File()
        f.load(id)
        response = StreamingHttpResponse(f.get(), content_type=f.meta["mimetype"])
        if not bool(request.GET.get("download", True)):
            response['Content-Disposition'] = 'attachment; filename=' + f.meta["filename"] 
        return response

class Update(PodaciView):
    template_name = "podaci/files/create.jinja"


class NoteAdd(PodaciView):
    template_name = None

    def get_context_data(self, id):
        self.file = File(self.fs)
        self.file.load(id)

        text = self.request.POST.get("note_text_markedup", "")
        if not text:
            return {"success": False, "error": "A comment cannot be empty."}

        success = self.file.add_note(text)
        meta = copy(self.file.meta)
        for note in meta["notes"]:
            u = get_user_model().objects.get(id=note["user"])
            note["user_details"] = {
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.first_name,
            }
            note["html"] = render_to_string("podaci/partials/_note.jinja", {"note": note})

        return {
            "success": True,
            "status": success,
            "meta": meta
        }

class NoteUpdate(PodaciView):
    template_name = None

    def get_context_data(self, id):
        self.file = File(self.fs)
        self.file.load(fid)
        return {'status': self.file.note_update(nid, text)}

class NoteDelete(PodaciView):
    template_name = None

    def get_context_data(self, fid, nid):
        self.file = File(self.fs)
        self.file.load(fid)
        return {'status': self.file.note_delete(nid)}

class MetaDataAdd(PodaciView):
    template_name = None

