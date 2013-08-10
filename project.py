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

git_setting()


class project_project(osv.osv):
    _inherit = 'project.project'

    _columns = {
        'git_setting_id': fields.many2one('git.setting', 'Git Setting'),
        'git_path': fields.char('Git Repository', size=256),
    }


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
