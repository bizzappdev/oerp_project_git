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
        pro_pool = self.pool.get('git.project')
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
            if not project_data['git_project_id']:
                cr_id = pro_pool.create(cr, uid, {
                    'git_path': project_data['git_url'],
                    'project_id': project_data['id'],
                    'git_setting_id': self_rec.id
                })
                self.pool.get('project.project').write(
                    cr, uid, project_data['id'], {'git_project_id': cr_id})
        return True

    def get_all_commits(self, cr, uid, ids, project, context={}):
        br_pool = self.pool.get('git.branch')
        cr_pool = self.pool.get('git.commit')
        for self_rec in self.browse(cr, uid, ids, context=context):
            project_path = os.path.join(
                self_rec.git_folder,
                project.git_path.split("/")[-1].split(".")[0])

            git_repo = git.Repo(project_path)
            git_pro_id = project.git_project_id.id
            for branches in git_repo.remote().refs:
                br_ids = br_pool.search(cr, uid,
                                        [('name', '=', branches.name),
                                         ('git_project_id', '=', git_pro_id)])
                if not br_ids:
                    br_ids = [br_pool.create(cr, uid, {
                        'name': branches.name,
                        'git_project_id': git_pro_id,
                    })]
                br_id = br_ids[0]
                for commit in git_repo.iter_commits(branches.name):
                    cr_ids = cr_pool.search(cr, uid,
                                            [('branch_id', '=', br_id),
                                             ('name', '=', commit.hexsha)])
                    if cr_ids:
                        continue
                    cr_pool.create(
                        cr, uid, {
                            'name':commit.hexsha,
                            'message': commit.message,
                            'author': str(commit.author),
                            'branch_id': br_id,
                            'git_id': self_rec.id,
                        })
        return True

git_setting()

class git_project(osv.osv):
    _name = 'git.project'
    _rec_name = "git_path"

    _columns = {
        'git_path': fields.char('Git Repository', size=256),
        'project_id': fields.many2one('project.project', 'Project'),
        'git_setting_id': fields.many2one('git.setting', 'Git Setting'),
        'branch_ids': fields.one2many('git.branch', 'git_project_id',
                                      'Branches'),

    }

git_project()


class project_project(osv.osv):
    _inherit = 'project.project'

    _columns = {
        'git_setting_id': fields.many2one('git.setting', 'Git Setting'),
        'git_path': fields.char('Git Repository', size=256),
        'git_project_id': fields.many2one('git.project', 'Git project'),
        'branch_id': fields.many2one('git.branch', 'Branch'),
        'commit_ids': fields.one2many('git.commit', 'project_id', 'Commits')
    }

    def onchange_branch(self, cr, uid, ids, branch_id, commit_ids, context={}):

        res = {'value':{}}
        if not branch_id:
            res['value']['commit_ids'] = []
            return res
        br_pool = self.pool.get('git.branch')
        cr_pool = self.pool.get('git.commit')
        if commit_ids:
            commit_ids = [x[1] for x in commit_ids]
            cr_pool.write(cr, uid, commit_ids, {'project_id': False})
        cr_ids = cr_pool.search(cr, uid, [('branch_id', '=', branch_id)])
        res['value']['commit_ids'] = cr_ids

        return res

    def get_git_repo(self, cr, uid, ids, context={}):
        sett_pool = self.pool.get('git.setting')
        set_ids = sett_pool.search(cr, uid, [])
        for self_rec in self.browse(cr, uid, ids, context=context):
            sett_pool.git_clone_pull(
                cr, uid, set_ids,
                {'git_url': self_rec.git_path, 'id': self_rec.id,
                 'git_project_id': (self_rec.git_project_id and
                                    self_rec.git_project_id.id or False)
                })
            cr.commit()
            self_rec = self.browse(cr, uid, self_rec.id, context=context)
            sett_pool.get_all_commits(cr, uid, set_ids, self_rec,
                                      context=context)
        return True

    def get_all_commits(self, cr, uid, ids, context={}):
        sett_pool = self.pool.get('git.setting')
        set_ids = sett_pool.search(cr, uid, [])
        for self_rec in self.browse(cr, uid, ids, context=context):
            sett_pool.get_commits(cr, uid, ids, self_rec, context=context)
        return True

project_project()


class git_branch(osv.osv):
    _name = 'git.branch'
    _columns = {
        'name': fields.char('Branch Name', size=256),
        'git_project_id': fields.many2one('git.project', 'Git project'),
        'commit_ids': fields.one2many('git.commit', 'branch_id', 'Commits'),
    }

git_branch()


class git_commit(osv.osv):
    _name = 'git.commit'
    _description = 'Git setting'

    _columns = {
        'git_id': fields.many2one("git.setting", "Project",
                                  ondelete='cascade'),
        'branch_id': fields.many2one('git.branch', 'Branch'),
        'name': fields.char('SHA', size=256, required=True),
        'author': fields.char('Author', size=256, required=True, select=True),
        'date': fields.datetime('Committed Time', select=True),
        'message': fields.char('Message', size=256, required=True,
                               select=True),
        'type': fields.selection([('ref', 'References'), ('close', 'Closes')]),
        'exception': fields.boolean("Exception"),
        'log': fields.text("Log"),
        'task_ids': fields.many2many('project.task', 'revision_task_rel',
                                     'rev_id', 'task_id',
                                     'Related Tasks', readonly=True),
        'project_id': fields.many2one('project.project', 'Projects')
    }

git_commit()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
