
class BaseCronJobController:
    def __init__(self, instance, model_class) -> None:
        """
        :param instance: instance of the related model eg: SavingPlan
        :param model_class: model class inhereted from BaseCronJob
        """
        self.instance = instance
        self.model_class = model_class
        self.scheduler = None
        self.cronjob = None

    def delete(self):
        cronjob = self.model_class.objects.get(pk=self.instance.id)

        try:
            self.scheduler.remove_job(cronjob.id)
        except:
            pass

        cronjob.delete()

    def execute(self):
        pass

    def main_process(self):
        pass
