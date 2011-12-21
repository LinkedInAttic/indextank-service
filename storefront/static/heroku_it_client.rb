# This module provides a heroku adapter for the indextank ruby gem
# All it does is use the 
require "indextank"
module IndexTank
    class HerokuClient < Client
        def initialize()
            super(ENV['INDEXTANK_API_URL'])
        end
    end
end
