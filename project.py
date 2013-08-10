# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp.osv import fields
import git
import os


class git_setting(osv.osv):
    _name = 'git.setting'
    _description = 'Git setting'

    _columns = {
        'name': fields.char("Name", size=64),
        'username': fields.char('Username', size=64, ),
        'password': fields.char('password', size=64, ),
        'git_folder': fields.char('Git Folder', size=256),
    }

    def get_url(self, git_url, user_name, password):
        if '@' in git_url:
            git_url = git_url.replace("@", ":%s@" % password)
        else:
            git_url = git_url.replace("//", "//%s:%s@" % (user_name, password))
        return git_url

    def clone_project(self, cr, uid, ids, project_data, context={}):
        for self_rec in self.browse(cr, uid, ids, context=context):
            git_url = self.get_url(project_data['git_url'], self_rec.username,
                                   self_rec.password)
            git_repo = git.Git()
            project_path = os.path.join(
                self_rec.git_folder,
                project_data['git_url'].split("/")[-1].split(".")[0])
            if os.path.exists(project_path):
                continue
            git_repo.clone(git_url, project_path)

        return True

    def pull_project(self, cr, uid, ids, project_data, context={}):
        for self_rec in self.browse(cr, uid, ids, context=context):
            project_path = os.path.join(
                self_rec.git_folder,
                project_data['git_url'].split("/")[-1].split(".")[0])
            if os.path.exists(project_path):
                git_pro = git.Repo(project_path)
                git_pro.remotes.origin.pull()

        return True

    def git_clone_pull(self, cr, uid, ids, project_data, context={}):
        for self_rec in self.browse(cr, uid, ids, context=context):
            project_path = os.path.join(
                self_rec.git_folder,
                project_data['git_url'].split("/")[-1].split(".")[0])
            if os.path.exists(project_path):
                self.pull_project(cr, uid, [self_rec.id], project_data,
                                  context=context)
            else:
                self.clone_project(cr, uid, [self_rec.id], project_data,
                                   context=context)
        return True

git_setting()


class project_project(osv.osv):
    _inherit = 'project.project'

    _columns = {
        'git_setting_id': fields.many2one('git.setting', 'Git Setting'),
        'git_path': fields.char('Git Repository', size=256),
    }

    def get_git_repo(self, cr, uid, ids, context={}):
        sett_pool = self.pool.get('git.setting')
        set_ids = sett_pool.search(cr, uid, [])
        for self_rec in self.browse(cr, uid, ids, context=context):
            sett_pool.git_clone_pull(
                cr, uid, set_ids,
                {'git_url': self_rec.git_path})
        return True

project_project()


class git_branch(osv.osv):
    _name = 'git.branch'
    _columns = {
        'name': fields.char('Branch Name', size=256),
    }

git_branch()


class git_commit(osv.osv):
    _name = 'git.commit'
    _description = 'Git setting'

    _columns = {
        'git_id': fields.many2one("git.setting", "Project",
                                  ondelete='cascade'),
        'name': fields.char('SHA', size=256, required=True),
        'author': fields.char('Author', size=256, required=True, select=True),
        'date': fields.datetime('Committed Time', required=True, select=True),
        'message': fields.char('Message', size=256, required=True,
                               select=True),
        'type': fields.selection([('ref', 'References'), ('close', 'Closes')]),
        'exception': fields.boolean("Exception"),
        'log': fields.text("Log"),
        'task_ids': fields.many2many('project.task', 'revision_task_rel',
                                     'rev_id', 'task_id',
                                     'Related Tasks', readonly=True),
    }

git_commit()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
